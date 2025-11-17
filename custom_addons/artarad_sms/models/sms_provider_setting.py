# -*- encoding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
from requests import Session

import suds
import json
import datetime
import pytz
from zeep import Client, Settings, helpers
from zeep.transports import Transport
import requests
from urllib.parse import urlencode
from typing import List, Dict, Optional

import logging

_logger = logging.getLogger(__name__)

api_urls = {"smsir": "",
            "ahra": "https://www.ahra.ir/webservice/ahrarest.svc/SendSms",
            "farapayamak": "https://rest.payamak-panel.com/api/SendSMS/SendSMS",
            "sepahansms": "http://www.sepahansms.com/sendSmsViaURL2.aspx",
            "adp": "http://ws.adpdigital.com/services/MessagingService?wsdl",
            "mavi": "https://ippanel.com/services.jspd",
            "faraz": "https://edge.ippanel.com/v1",
            "hooshmand": "http://smswbs.ir/class/sms/restful/sendSms_OneToMany.php",
            "amoot": "https://portal.amootsms.com/webservice2.asmx/SendSimple_REST",
            "asanak": "https://panel.asanak.com/webservice/v1rest/sendsms",
            "kaveh": "https://api.kavenegar.com/v1",
            "rahyab": "http://www.linepayamak.ir/Post/Send.asmx?wsdl",
            "mehrafraz": "https://mehrafraz.com/fullrest/api/Send",
            }


class artaradSmsProviderSetting(models.Model):
    _name = "artarad.sms.provider.setting"
    _description = "Iranian SMS Provider Setting"
    _order = "sequence"

    sequence = fields.Integer(default=0)
    provider = fields.Selection([("smsir", "SMS.IR"), ("farapayamak", "Farapayamak"),
                                 ("sepahansms", "SepahanSMS"), ("adp", "Atieh Dadeh Pardaz"), ("mavi", "MaviSMS"),
                                 ("faraz", "FarazSMS"), ("hooshmand", "SMSHooshmand"), ("amoot", "AmootSMS"),
                                 ("asanak", "Asanak"), ("ahra", "Ahra"), ("mehrafraz", "MehrAfraz"),
                                 ("rahyab", "Rahyab"), ("kaveh", "Kaveh Negar")], required="True")
    api_url = fields.Char("API URL", required="True")
    from_number = fields.Char(required="True")
    username = fields.Char(required="True")
    password = fields.Char(required="True")
    domain = fields.Char()

    @api.onchange("provider")
    def onchange_provider(self):
        self.api_url = api_urls.get(self.provider, False)

    def send_sms(self, number, message):
        return getattr(self, f"send_sms_by_{self.provider}")(number, message)

    def send_sms_by_mehrafraz(self, number, message):

        url =self.api_url
        mobiles = number if isinstance(number, (list, tuple)) else [number]
        client_id =0
        payload = {
            "UserName": self.username,
            "Password": self.password,
            "DomainName": self.domain,
            "Smsbody": message,
            "Mobiles": mobiles,
            "SenderNumber":self.from_number,
            "Id": client_id,
        }

        headers = {"Content-Type": "application/json"}

        try:
            resp = requests.post(url, data=json.dumps(payload), headers=headers, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            _logger.exception("Mehrafraz: HTTP error while sending SMS to %s: %s", mobiles, e)
            return False
        try:
            data = resp.json()
        except Exception:
            _logger.error("Mehrafraz: non-JSON response (body=%s)", resp.text)
            return False
        status = data.get("Status")
        ok = (status == 0) and bool(data.get("ReturnCodes"))
        if ok:
            _logger.info("Mehrafraz: SMS sent to %s, return_codes=%s, id=%s",
                         mobiles, data.get("ReturnCodes"), client_id)
            return True
        else:
            msg = data.get("Messege") or data.get("Message") or "Unknown error"
            _logger.error("Mehrafraz: failed to send SMS. status=%s, message=%s, body=%s, id=%s",
                          status, msg, data, client_id)
            return False

    def send_sms_by_rahyab(self, number, message):

        session = Session()
        session.verify = True
        client = Client(wsdl=self.api_url, transport=Transport(session=session, timeout=20))

        try:
            to_arr = client.get_type("ns0:ArrayOfString")(string=number)
            resp = client.service.SendSms(
                self.username,
                self.password,
                to_arr,
                self.from_number,
                message,
                False,
                "",
                None,
                None
            )
            if resp.SendSmsResult==1:
              _logger.info(f"successul sms send to {number}")
              return True
            else:
               _logger.error(f"unsuccessul sms send to {number} : SendSmsResult{resp.SendSmsResult}")
               return False
        except Exception as e:
            _logger.error(f"unsuccessul sms send to {number} : {e}")
            return False

    def send_sms_by_kaveh(self, number, message):
        normalized = message.replace("،", ",").strip()
        parts = [p.strip() for p in normalized.split(",") if p.strip()]
        template = parts[-1]
        tokens = parts[:-1]  # ممکن است 1 تا N باشد
        params = {
            "receptor": number,
            "template": template,
        }
        if len(tokens) >= 1: params["token"] = tokens[0]
        if len(tokens) >= 2: params["token10"] = tokens[1]
        if len(tokens) >= 3: params["token20"] = tokens[2]
        base = f"https://api.kavenegar.com/v1/{self.password}/verify/lookup.json"

        response = requests.get(f"{base}?{urlencode(params)}")

        if response.status_code == 200:
            _logger.info(f"successul sms send to {number}")
            return True
        else:
            _logger.error(f"unsuccessul sms send to {number} due to {response.status_code}")
            return False

    def send_sms_by_smsir(self, number, message):
        authen_data = {"UserApiKey": self.password,
                       "SecretKey": self.username}
        json_authen = requests.post("http://RestfulSms.com/api/Token",
                                    data=json.dumps(authen_data),
                                    headers={"Content-type": "application/json"})
        authen = json.loads(json_authen.content)

        if authen["IsSuccessful"]:
            message_data = {"MobileNumbers": [number],
                            "Messages": [message],
                            "LineNumber": self.from_number,
                            "SendDateTime": "",
                            "CanContinueInCaseOfError": "false"}
            json_response = requests.post(self.api_url,
                                          data=json.dumps(message_data),
                                          headers={"Content-type": "application/json",
                                                   "x-sms-ir-secure-token": authen["TokenKey"]})
            response = json.loads(json_response.content)
            if (response.sjta):
                _logger.info(f"successul sms send to {number}")
                return True
            else:
                _logger.error(f"unsuccessul sms send to {number} due to {response['Message']}")
                return False
        else:
            _logger.error(f"unsuccessul sms authentication to {self.provider} due to {authen['Message']}")
            return False

    def send_sms_by_ahra(self, number, message):
        response = requests.get(
            "https://www.ahra.ir/sms2.aspx?&username=%s&password=%s&to=%s&text=%s" % (self.username, self.password,
                                                                                      number, message))
        if response.status_code == 200:
            _logger.info(f"successul sms send to {number}")
            return True
        else:
            _logger.error(f"unsuccessul sms send to {number} due to {response.status_code}")
            return False

    def send_sms_by_farapayamak(self, number, message):
        message_data = {"username": self.username,
                        "password": self.password,
                        "to": number,
                        "from": self.from_number,
                        "text": message,
                        "isflash": "false"}
        response = requests.post(self.api_url,
                                 data=json.dumps(message_data),
                                 headers={"Content-type": "application/json"})
        if response.status_code == 200:
            _logger.info(f"successul sms send to {number}")
            return True
        else:
            _logger.error(f"unsuccessul sms send to {number} due to {response.status_code}")
            return False

    def send_sms_by_sepahansms(self, number, message):
        message_data = {"userName": self.username + ";sepahansms",
                        "password": self.password,
                        "senderNumber": self.from_number,
                        "reciverNumber": number,
                        "smsText": message, }
        response = requests.post(self.api_url,
                                 data=message_data)
        if response.status_code == 200:
            _logger.info(f"successul sms send to {number}")
            return True
        else:
            _logger.error(f"unsuccessul sms send to {number} due to {response.status_code}")
            return False

    def send_sms_by_adp(self, number, message):
        client = suds.client.Client(self.api_url)
        response = client.service.send(userName=self.username, password=self.password, shortNumber=self.from_number,
                                       destNo=number, messageType=1, encoding=2, longSupported=True,
                                       dueTime=datetime.datetime.now(), content=message)

        if response.status == 0:
            _logger.info(f"successul sms send to {number}")
            return True
        else:
            _logger.error(f"unsuccessul sms send to {number} due to {response.status}")
            return False

    def send_sms_by_mavi(self, number, message):
        message_data = {"uname": self.username,
                        "pass": self.password,
                        "from": self.from_number,
                        "to": number,
                        "message": message,
                        "op": "send", }
        response = requests.post(self.api_url,
                                 data=message_data)
        if response.status_code == 200 and json.loads(response.content.decode())[0] == 0:
            _logger.info(f"successul sms send to {number}")
            return True
        else:
            _logger.error(f"unsuccessul sms send to {number} due to {json.loads(response.content.decode())[1]}")
            return False

    def send_sms_by_faraz(self, number, message):
        authen_data = {"username": self.username,
                       "password": self.password}
        json_authen = requests.post(self.api_url + "/api/acl/auth/login",
                                    data=json.dumps(authen_data),
                                    headers={"Content-type": "application/json"})
        authen = json.loads(json_authen.content)

        message_data = {"sending_type": 'webservice',
                        "from_number": self.from_number,
                        "params": {
                            "recipients": [number]
                        },
                        "message": message,
                        }
        response = requests.post(self.api_url + "/api/send",
                                 data=json.dumps(message_data),
                                 headers={"Content-type": "application/json", "Authorization": authen['data']['token']})
        if response.status_code == 200 and response['meta']['status']:
            _logger.info(f"successul sms send to {number}")
            return True
        else:
            _logger.error(f"unsuccessul sms send to {number} due to {response.text}")
            return False

    def send_sms_by_hooshmand(self, number, message):
        message_data = {
            "uname": self.username,
            "pass": self.password,
            "from": self.from_number,
            "to": [number],
            "msg": message
        }

        response = requests.post(self.api_url, headers={"Content-Type": "application/json"},
                                 data=json.dumps(message_data))
        if response.status_code == 200 and json.loads(response.text)["errCode"] == 0:
            _logger.info(f"successul sms send to {number}")
            return True
        else:
            _logger.error(f"unsuccessul sms send to {number} due to {json.loads(response.content.decode())[1]}")
            return False

    def send_sms_by_amoot(self, number, message):
        message_data = (f"?UserName={self.username}"
                        f"&Password={self.password}"
                        f"&SendDateTime={datetime.datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Asia/Tehran')).strftime('%Y-%m-%d %H:%M:%S')}"
                        f"&SMSMessageText={message}"
                        f"&LineNumber={self.from_number}"
                        f"&Mobiles={number}")

        response = requests.get(self.api_url + message_data)
        if response.status_code == 200 and json.loads(response.text)["Status"] == "Success":
            _logger.info(f"successul sms send to {number}")
            return True
        else:
            _logger.error(f"unsuccessul sms send to {number} due to {json.loads(response.content.decode())[1]}")
            return False

    def send_sms_by_asanak(self, number, message):
        message_data = {"username": self.username,
                        "password": self.password,
                        "source": self.from_number,
                        "destination": number,
                        "message": message, }
        response = requests.post(self.api_url,
                                 data=message_data)
        if response.status_code == 200 and response.text.find('[') != -1:
            _logger.info(f"successul sms send to {number}")
            return True
        else:
            _logger.error(f"unsuccessul sms send to {number} due to {response.status_code}")
            return False