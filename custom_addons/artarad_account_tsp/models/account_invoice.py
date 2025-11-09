# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _

import datetime
import requests

from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey import RSA
from Cryptodome.Signature import pkcs1_15

from Cryptodome.Random import get_random_bytes
from Cryptodome.Cipher import AES

from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.Signature import pss

import base64
import math

import uuid
import json
import re

import logging
_logger = logging.getLogger(__name__)

SERVER_BASE_URL = {
    "primary": "https://tp.tax.gov.ir/req/api/self-tsp/",
    "test": "https://sandboxrc.tax.gov.ir/req/api/self-tsp/"
}

class artaradAccountInvoice(models.Model):
    _inherit = "account.move"

    #####################
    # Additional Fields #
    #####################
    tsp_taxid = fields.Char(string="TaxID", tracking=True, readonly=True, copy=False)
    tsp_temp_taxid = fields.Char(string="Temporary TaxID", readonly=True, copy=False)
    tsp_type = fields.Selection([("1", "اول"),
                                  ("2", "دوم")], tracking=True, copy=False)
    tsp_pattern = fields.Selection([("1", "فروش"),
                                  ("2", "فروش ارزی"),
                                  ("7", "صادرات")], tracking=True, copy=False)
    tsp_state = fields.Selection([("not_sent", "Null"),

                                  ("pending_send", "Submit Pending"),
                                  ("accepted_send", "Submit Accepted"), 
                                  ("rejected_send", "Submit Rejected"),

                                  ("pending_edit", "Edit Pending"),
                                  ("accepted_edit", "Edit Accepted"), 
                                  ("rejected_edit", "Edit Failed"),

                                  ("pending_cancel", "Revoke Pending"),
                                  ("accepted_cancel", "Revoke Accepted"), 
                                  ("rejected_cancel", "Revoke Failed"),
                                  ], default="not_sent", tracking=True, readonly=True, copy=False)
    tsp_reference_number = fields.Char(string="Reference Number", tracking=True, readonly=True, copy=False)
    tsp_description = fields.Text(string="Description", readonly=True, copy=False)

    @api.constrains("partner_id")
    def _tsp_load_default_type_and_pattern(self):
        for rec in self:
          if rec.partner_id:
              rec.tsp_type = rec.partner_id.tsp_default_type
              rec.tsp_pattern = rec.partner_id.tsp_default_pattern

    @api.onchange("tsp_type")
    def _tsp_empty_pattern(self):
        if self.tsp_type == "3":
            self.tsp_pattern = False

    ####################
    # Overrided Fields #
    ####################
    reversed_entry_id = fields.Many2one('account.move', string="Reversal of", readonly=False, copy=False,
        check_company=True)

    #############################
    # Monetary Helper Functions #
    #############################
    def tsp_get_rials(self, amount):
        return int(self.currency_id._convert(amount, self.company_id.currency_id, self.company_id, self.invoice_date, False))

    def tsp_get_amount_before_discount(self, line):
        # return self.tsp_get_rials(line.price_unit * line.quantity)
        return self.tsp_get_rials(round(line.price_unit * line.quantity))
        
    def tsp_get_amount_discount(self, line):
        # if line.discount:
        #     return max(self.tsp_get_rials(line.price_unit * line.quantity) - self.tsp_get_rials(line.price_subtotal), 0)
        # return 0
        return self.tsp_get_amount_before_discount(line) - self.tsp_get_rials(line.price_subtotal)
        
    def tsp_get_amount_after_discount(self, line):
        return self.tsp_get_amount_before_discount(line) - self.tsp_get_amount_discount(line)
        
    def tsp_get_amount_tax(self, line):
        if line.tax_ids:
            return self.tsp_get_rials(self.tsp_get_amount_after_discount(line) * (sum(line.tax_ids.mapped("amount")) / 100))
        return 0

    def tsp_get_amount_total(self, line):
        return self.tsp_get_amount_after_discount(line) + self.tsp_get_amount_tax(line)

    ################################
    # Invoice Dictionary Functions #
    ################################
    def tsp_get_indatim(self):
        return int(str(int(datetime.datetime.timestamp(datetime.datetime.combine(self.invoice_date, datetime.time(12,30,1)))*1000)))

    def tsp_get_indati2m(self):
        if self.tsp_pattern == "1":
            return self.tsp_get_indatim()
        return None
        
    def tsp_get_setm(self):
        if self.tsp_pattern != "7":
            return 1
        return None

    def tsp_get_cap(self):
        if self.tsp_pattern == "1":
            return sum([self.tsp_get_amount_total(line) for line in self.invoice_line_ids.filtered(lambda i: i.product_id)])
        return None
        
    def tsp_get_bid(self):
        if self.tsp_pattern != "7":
            if self.partner_id.company_type != "company":
                return self.partner_id.national_number or None
        return None

    def tsp_get_bpc(self):
        if self.tsp_pattern != "7":
            if self.partner_id.company_type != "company":
                return self.partner_id.zip or None
        return None
    
    def tsp_get_taxid(self):
        def compute_verhoeff(number_string):
            number_string = number_string[::-1]

            # multiplication table
            d = (
                (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
                (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
                (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
                (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
                (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
                (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
                (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
                (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
                (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
                (9, 8, 7, 6, 5, 4, 3, 2, 1, 0)
            )

            # permutation table
            p = (
                (0, 1, 2 ,3 ,4 ,5 ,6 ,7 ,8 ,9),
                (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
                (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
                (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
                (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
                (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
                (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
                (7, 0, 4, 6, 9, 1, 3, 2, 5, 8)
            )

            # inverse table
            inv = (0, 4 ,3 ,2 ,1 ,5 ,6 ,7 ,8 ,9)

            c = 0
            for i in range(len(number_string)):
                c = d[c][p[(i+1)%8][int(number_string[i])]]
            return inv[c]

        taxid_part1 = self.company_id.tsp_unique_id
        taxid_part2 = hex((self.invoice_date - datetime.date(1970,1,1)).days)[2:].zfill(5)
        taxid_part3 = hex(int(self.env['ir.sequence'].next_by_code('tsp.invoice.serial')))[2:].zfill(10)
        taxid_part4 = compute_verhoeff(f"{ord(taxid_part1[0]) if 65 <= ord(taxid_part1[0]) <= 90 else taxid_part1[0]}" +\
                            f"{ord(taxid_part1[1]) if 65 <= ord(taxid_part1[1]) <= 90 else taxid_part1[1]}" +\
                            f"{ord(taxid_part1[2]) if 65 <= ord(taxid_part1[2]) <= 90 else taxid_part1[2]}" +\
                            f"{ord(taxid_part1[3]) if 65 <= ord(taxid_part1[3]) <= 90 else taxid_part1[3]}" +\
                            f"{ord(taxid_part1[4]) if 65 <= ord(taxid_part1[4]) <= 90 else taxid_part1[4]}" +\
                            f"{ord(taxid_part1[5]) if 65 <= ord(taxid_part1[5]) <= 90 else taxid_part1[5]}" +\
                            f"{int(taxid_part2,base=16)}".zfill(6) +\
                            f"{int(taxid_part3,base=16)}".zfill(12))

        return f"{taxid_part1}{taxid_part2}{taxid_part3}{taxid_part4}".upper()
    
    def tsp_get_tprdis(self):
        if self.tsp_pattern != "7":
            return sum([self.tsp_get_amount_before_discount(line) for line in self.invoice_line_ids.filtered(lambda i: i.product_id)])
        return None
    
    def tsp_get_tdis(self):
        if self.tsp_pattern != "7":
            return sum([self.tsp_get_amount_discount(line) for line in self.invoice_line_ids.filtered(lambda i: i.product_id)])
        return None

    def tsp_get_tadis(self):
        if self.tsp_pattern != "7":
            return sum([self.tsp_get_amount_after_discount(line) for line in self.invoice_line_ids.filtered(lambda i: i.product_id)])
        return None

    def tsp_get_tvam(self):
        if self.tsp_pattern != "7":
            return sum([self.tsp_get_amount_tax(line) for line in self.invoice_line_ids.filtered(lambda i: i.product_id)])
        return 0
    
    def tsp_get_tbill(self):
        return sum([self.tsp_get_amount_total(line) for line in self.invoice_line_ids.filtered(lambda i: i.product_id)])
    
    def tsp_get_tob(self):
        if self.tsp_pattern != "7":
            if self.partner_id.company_type != "company":
                return 1
            else:
                return 2
        return None
    
    def tsp_get_tinb(self):
        if self.tsp_pattern != "7":
            if self.partner_id.company_type == "company":
                return self.partner_id.national_number or None
        return None

    def tsp_get_tonw(self):
        if self.tsp_pattern == "7":
            return sum([round((line.product_id.weight or 0) * line.quantity, 8) for line in self.invoice_line_ids.filtered(lambda i: i.product_id)]) or None
        return None
    
    def tsp_get_torv(self):
        if self.tsp_pattern == "7":
            return self.tsp_get_tbill()
        return None
    
    def tsp_get_tocv(self):
        if self.tsp_pattern == "7":
            return sum(self.invoice_line_ids.filtered(lambda i: i.product_id).mapped("price_total"))
        return None
    
    def tsp_get_fee(self, line):
        if self.tsp_pattern != "7":
            return self.tsp_get_rials(line.price_unit)
        return None
    
    def tsp_get_cfee(self, line):
        if self.tsp_pattern != "7":
            return line.price_unit
        return None
    
    def tsp_get_prdis(self, line):
        if self.tsp_pattern != "7":
            return self.tsp_get_amount_before_discount(line)
        return None

    def tsp_get_dis(self, line):
        if self.tsp_pattern != "7":
            return self.tsp_get_amount_discount(line)
        return None
    
    def tsp_get_adis(self, line):
        if self.tsp_pattern != "7":
            return self.tsp_get_amount_after_discount(line)
        return None

    def tsp_get_vra(self, line):
        if self.tsp_pattern != "7":
            return int(sum(line.tax_ids.mapped("amount")))
        return 0

    def tsp_get_vam(self, line):
        if self.tsp_pattern != "7":
            return self.tsp_get_amount_tax(line)
        return 0
    
    def tsp_get_nw(self, line):
        if self.tsp_pattern == "7":
            return round((line.product_id.weight or 0) * line.quantity, 8) or None
        return None
    
    def tsp_get_ssrv(self, line):
        if self.tsp_pattern == "7":
            return self.tsp_get_amount_total(line)
        return None
    
    def tsp_get_sscv(self, line):
        if self.tsp_pattern == "7":
            return line.price_total
        return None
    
    def tsp_get_iinn(self, payment):
        if self.tsp_type == "3":
            return None
        return None

    def tsp_get_acn(self, payment):
        if self.tsp_type == "3":
            return None
        return None

    def tsp_get_trmn(self, payment):
        if self.tsp_type == "3":
            return None
        return None

    def tsp_get_trn(self, payment):
        if self.tsp_type == "3":
            return None
        return None

    def tsp_get_pcn(self, payment):
        if self.tsp_type == "3":
            return None
        return None

    def tsp_get_pid(self, payment):
        if self.tsp_type == "3":
            return None
        return None

    def tsp_get_pdt(self, payment):
        if self.tsp_type == "3":
            return None
        return None

    def tsp_get_pv(self, payment):
        if self.tsp_type == "3":
            return None
        return None

    def tsp_get_pmt(self, payment):
        if self.tsp_type == "3":
            return None
        return None

    def tsp_get_invoice_dictionary(self):
        invoice_dictionary = {
            "header": {
                "indati2m": self.tsp_get_indati2m(), # تاریخ و زمان ایجاد صورتحساب (میلادی)
                "indatim": self.tsp_get_indatim(), # تاریخ و زمان صدور صورتحساب (میلادی)
                "inty": int(self.tsp_type), # نوع صورتحساب (1 یا 2 یا 3)
                "ft": None, # نوع پرواز
                "inno": None, # سریال صورتحساب داخلی حافظه مالیاتی
                "irtaxid": ..., # شماره منحصر به فرد مالیاتی صورتحساب مرجع
                "scln": None, # شماره پروانه گمرکی
                "setm": self.tsp_get_setm(), # روش تسویه (1: نقد، 2: نسیه، 3: نقد و نسیه)
                "tins": self.company_id.partner_id.national_number, # شماره اقتصادی (فعلا همان شماره ملی) فروشنده
                "cap":  self.tsp_get_cap(), # مبلغ پرداختی نقدی
                "bid": self.tsp_get_bid(), # شماره / شناسه ملی خریدار
                "insp": None, # مبلغ پرداختی نسیه
                "tvop": None, # مجموع سهم مالیات بر ارزش افزوده از پرداخت
                "bpc": self.tsp_get_bpc(), # کد پستی خریدار
                "tax17": None, # مالیات موضوع ماده 17
                "taxid": self.tsp_get_taxid(), # شماره منحصر به فرد مالیاتی
                "inp": int(self.tsp_pattern) or None, # الگوی صورتحساب (1: فروش، 2: فروش ارزی، 3: طلا و جواهر، 4: پیمانکاری، 5: قبض خدماتی، 6: بلیط هواپیما)
                "scc": None, # کد گمرک محل اظهار
                "ins": ..., # موضوع صورتحساب (1: اصلی، 2: اصلاحی، 3: ابطالی، 4: برگشت از فروش)
                "billid": None, # شماره اشتراک / شناسه قبض بهره بردار
                "tprdis": self.tsp_get_tprdis(), # مجموع مبلغ قبل از کسر تخفیف
                "tdis": self.tsp_get_tdis(), # مجموع تخفیفات
                "tadis": self.tsp_get_tadis(), # مجموع مبلغ پس از کسر تخفیف
                "tvam": self.tsp_get_tvam(), # مجموع مالیات بر ارزش افزوده
                "todam": 0, # مجموع سایر مالیات و عوارض
                "tbill": self.tsp_get_tbill(), # مجموع صورتحساب
                "tob": self.tsp_get_tob(), # نوع شخص خریدار (1: حقیقی، 2: حقوقی، 3: مشارکت مدنی، 4: اتباع، 5: مصرف کننده نهایی)
                "tinb": self.tsp_get_tinb(), # شماره اقتصادی (فعلا همان شماره ملی) خریدار
                "sbc": None, # کد شعبه فروشنده
                "bbc": None, # کد شعبه خریدار
                "bpn": None, # شماره گذرنامه خریدار
                "crn": None, # شناسه یکتای ثبت قرارداد فروشنده
                "cdcn": None, # شماره کوتاژ اظهارنامه گمرکی
                "cdcd": None, # تاریخ کوتاژ اظهارنامه گمرکی
                "tonw": self.tsp_get_tonw(), # مجموع وزن خالص
                "torv": self.tsp_get_torv(), # مجموع ارزش ریالی
                "tocv": self.tsp_get_tocv(), # مجموع ارزش ارزی
            }, 
            "body": [{
                "sstid": (self.company_id.tsp_product_code_reference == "product_template" and line.product_id.product_tmpl_id.tsp_code) or line.product_id.tsp_variant_code, # شناسه کالا / خدمت
                "sstt": line.name.replace(" ", "") if self.company_id.tsp_include_description else None, # شرح کالا / خدمت
                "mu": (self.company_id.tsp_include_uom and line.product_uom_id.tsp_code) or None, # واحد اندازه گیری
                "am": line.quantity, # تعداد / مقدار
                "fee": self.tsp_get_fee(line), # مبلغ واحد
                "cfee": self.tsp_get_cfee(line), # میزان ارز
                "cut": self.currency_id.name, # نوع ارز
                "exr": self.tsp_get_rials(1), # نرخ برابری ارز با ریال
                "prdis": self.tsp_get_prdis(line), # مبلغ قبل از تخفیف
                "dis": self.tsp_get_dis(line), # مبلغ تخفیف
                "adis": self.tsp_get_adis(line), # مبلغ پس از تخفیف
                "vra": self.tsp_get_vra(line), # نرخ مالیات بر ارزش افزوده
                "vam": self.tsp_get_vam(line), # مبلغ مالیات بر ارزش افزوده
                "odt": None, # موضوع سایر مالیات و عوارض
                "odr": None, # نرخ سایر مالیات و عوارض
                "odam": None, # مبلغ سایر مالیات و عوارض
                "olt": None, # موضوع سایر وجوه قانونی
                "olr": None, # نرخ سایر وجوه قانونی
                "olam": None, # مبلغ سایر وجوه قانونی
                "consfee": None, # اجرت ساخت
                "spro": None, # سود فروشنده
                "bros": None, # حق العمل
                "tcpbs": None, # مبلغ کل اجرت، حق العمل و سود
                "cop": None, # سهم نقدی از پرداخت
                "bsrn": None, # شناسه یکتای ثبت قرارداد حق العمل کاری
                "vop": None, # سهم ارزش افزوده از پرداخت
                "tsstam": self.tsp_get_amount_total(line), # مبلغ کل کالا / خدمت
                "nw": self.tsp_get_nw(line), # وزن خالص
                "ssrv": self.tsp_get_ssrv(line), # ارزش ریالی کالا
                "sscv": self.tsp_get_sscv(line), # ارزش ارزی کالا
            } for line in self.invoice_line_ids.filtered(lambda i: i.product_id)],
            "payments": [{
                "iinn": self.tsp_get_iinn(payment), # شماره سوییچ پرداخت
                "acn": self.tsp_get_acn(payment), # شماره پذیرنده فروشگاهی
                "trmn": self.tsp_get_trmn(payment), # شماره پایانه
                "trn": self.tsp_get_trn(payment), # شماره پیگیری
                "pcn": self.tsp_get_pcn(payment), # شماره کارت پرداخت کننده
                "pid": self.tsp_get_pid(payment), # شماره / شناسه ملی پرداخت کننده
                "pdt": self.tsp_get_pdt(payment), # تاریخ و زمان پرداخت صورتحساب
                "pv": self.tsp_get_pv(payment), # مبلغ پرداختی
                "pmt": self.tsp_get_pmt(payment), # روش پرداخت
            } for payment in self.payment_ids] if self.tsp_type == "3" else 
                [{"iinn": None, 
                  "acn": None, 
                  "trmn": None, 
                  "trn": None, 
                  "pcn": None, 
                  "pid": None, 
                  "pdt": None, 
                  "pv": None, 
                  "pmt": None}],
            "extension": None
        }

        _logger.info("TSP: " + str(invoice_dictionary))
        return invoice_dictionary


    def tsp_get_dictionary_normalized(self, dictionary):

        def flatten_dictionary(dictionary, parent_key=""):
            result = {}

            if not isinstance(dictionary, dict):
                result[parent_key] = dictionary
            else:
                for key in dictionary:
                    superkey = key if not parent_key else f"{parent_key}.{key}"

                    if (not isinstance(dictionary[key], dict)) and (not isinstance(dictionary[key], list)):
                        result[superkey] = dictionary[key]
                    elif isinstance(dictionary[key], dict):
                        result.update(flatten_dictionary(dictionary[key], superkey))
                    elif isinstance(dictionary[key], list):
                        for index, item in enumerate(dictionary[key]):
                            result.update(flatten_dictionary(item, f"{superkey}.E{index}"))

            return result
        
        dictionary = flatten_dictionary(dictionary)

        result = ""
        for key in sorted(dictionary.keys()):
            if dictionary[key]:
                if isinstance(dictionary[key], str) and "#" in dictionary[key]:
                    result += f"{dictionary[key].replace('#', '##')}"
                else:
                    result += f"{dictionary[key]}"
            else:
                if isinstance(dictionary[key], bool):
                    result += "false"
                elif isinstance(dictionary[key], int):
                    result += "0"
                else: # None
                    result += "#"
            result += "#"
        result = result[:-1]
        
        return result


    def tsp_get_signed_string(self, string):
        try:
            key = RSA.import_key(self.company_id.tsp_private_key)
            h = SHA256.new(string.encode("utf8"))
            signature = pkcs1_15.new(key).sign(h)
            base64_bytes = base64.b64encode(signature)
            base64_signature = base64_bytes.decode("utf8")
            return base64_signature
        except:
            raise exceptions.ValidationError(_("Invalid value for PrivateKey in settings of accounting!"))


    def tsp_sync_get_server_info(self):
        ts = str(int(datetime.datetime.timestamp(datetime.datetime.now())*1000))
        headers = {
            "requestTraceId": ts,
            "timestamp": ts,
        }

        body = {
            "time": 1,
            "packet": {
                "uid": None,
                "packetType": "GET_SERVER_INFORMATION",
                "retry": False,
                "data": None,
                "encryptionKeyId": "",
                "symmetricKey": "",
                "iv": "",
                "fiscalId": "",
                "dataSignature": ""
            }
        }

        response = requests.post(SERVER_BASE_URL[self.company_id.tsp_server_mode] + "sync/GET_SERVER_INFORMATION", headers=headers, json=body)

        try:
            response_json = response.json()
        except:
            raise exceptions.AccessError(_("TSP server is not reachable!"))
        
        try:
            return "-----BEGIN PUBLIC KEY-----\n" +\
                   re.sub("(.{64})", "\\1\n", response_json["result"]["data"]["publicKeys"][0]["key"], 0, re.DOTALL) +\
                   "\n-----END PUBLIC KEY-----", response_json["result"]["data"]["publicKeys"][0]["id"]
        except:
            raise exceptions.ValidationError(response_json["errors"][0]["message"])


    def tsp_sync_get_token(self):
        ts = str(int(datetime.datetime.timestamp(datetime.datetime.now())*1000))
        headers = {
            "requestTraceId": ts,
            "timestamp": ts
        }

        body = {
            "packet": {
                "uid": None,
                "packetType": "GET_TOKEN",
                "retry": False,
                "data": {
                    "username": self.company_id.tsp_unique_id,
                },
                "encryptionKeyId": "",
                "symmetricKey": "",
                "iv": "",
                "fiscalId": "",
                "dataSignature": ""
            },
        }
        body["signature"] = self.tsp_get_signed_string(self.tsp_get_dictionary_normalized({**body["packet"], **headers}))

        response = requests.post(SERVER_BASE_URL[self.company_id.tsp_server_mode] + "sync/GET_TOKEN", headers=headers, json=body)

        try:
            response_json = response.json()
        except:
            raise exceptions.AccessError(_("TSP server is not reachable!"))
        
        try:
            return response_json["result"]["data"]["token"]
        except:
            raise exceptions.ValidationError(response_json["errors"][0]["message"])


    def tsp_check_constraints(self):
        if (not self.company_id.tsp_unique_id) or (not self.company_id.tsp_private_key):
            raise exceptions.ValidationError(_("Fill in the UniqueID and PrivateKey fields in settings of accounting!"))

        if not self.invoice_date:
            raise exceptions.ValidationError(_("Fill in the Invoice Date field in the invoice!"))

        if not self.tsp_type:
            raise exceptions.ValidationError(_("Fill in the Type field in the invoice!"))
        
        if self.tsp_type in ("1", "2") and not self.tsp_pattern:
            raise exceptions.ValidationError(_("Fill in the Pattern field in the invoice!"))

        if self.tsp_type in ("1", "2") and (any([(self.company_id.tsp_product_code_reference == "product_template" and not line.product_id.product_tmpl_id.tsp_code) or (self.company_id.tsp_product_code_reference == "product_product" and not line.product_id.tsp_variant_code) for line in self.invoice_line_ids.filtered(lambda i: i.product_id)])):
            raise exceptions.ValidationError(_("Fill in the TSP Code for all products used in the invoice!"))

        if not self.company_id.partner_id.national_number:
            raise exceptions.ValidationError(_("Fill in the National Number/ID of the your company!"))

        if self.tsp_type == "1" and self.tsp_pattern != "7" and not self.partner_id.national_number:
            raise exceptions.ValidationError(_("Fill in the National Number/ID of the partner!"))

        if self.tsp_type == "2" and self.tsp_pattern != "1":
            raise exceptions.ValidationError(_("When the type is دوم, The only valid pattern is فروش!"))


    def tsp_sync_inquiry(self):
        self.tsp_check_constraints()

        ts = str(int(datetime.datetime.timestamp(datetime.datetime.now())*1000))
        headers = {
            "requestTraceId": ts,
            "timestamp": ts,
            "Authorization": self.tsp_sync_get_token()
        }
        
        body = {
            "time": 1,
            "packet": {
                "uid": "",
                "packetType": "INQUIRY_BY_REFERENCE_NUMBER",
                "retry": False,
                "data": {
                    "referenceNumber": [self.tsp_reference_number],
                },
                "encryptionKeyId": "",
                "symmetricKey": "",
                "iv": "",
                "fiscalId": self.company_id.tsp_unique_id,
                "dataSignature": ""
            },
        }

        body["signature"] = self.tsp_get_signed_string(self.tsp_get_dictionary_normalized({**body["packet"], **headers}))
        headers["Authorization"] = "Bearer " + headers["Authorization"]

        response = requests.post(SERVER_BASE_URL[self.company_id.tsp_server_mode] + "sync/INQUIRY_BY_REFERENCE_NUMBER", headers=headers, json=body)

        try:
            response_json = response.json()
        except:
            raise exceptions.AccessError(_("TSP server is not reachable!"))
        else:
            _logger.info("TSP: " + str(response_json))
            try:
                response_status = response_json["result"]["data"][0]["status"]
            except:
                raise exceptions.AccessError(str(response_json))
            else:
                if response_status == "PENDING":
                    pass # keep previous state
                elif response_status == "SUCCESS":
                    self.tsp_taxid = self.tsp_temp_taxid
                    if self.tsp_state == "pending_send":
                        self.tsp_state = "accepted_send"
                    elif self.tsp_state == "pending_edit":
                        self.tsp_state = "accepted_edit"
                    elif self.tsp_state == "pending_cancel":
                        self.tsp_state = "accepted_cancel"
                elif response_status == "FAILED":
                    if self.tsp_state == "pending_send":
                        self.tsp_state = "rejected_send"
                    # elif self.tsp_state == "pending_edit":
                    #     self.tsp_state = "rejected_edit"
                    # elif self.tsp_state == "pending_cancel":
                    #     self.tsp_state = "rejected_cancel"
                    elif self.tsp_state in ("pending_edit", "pending_cancel"):
                        self.tsp_state = "accepted_send"

                    enter = "\n"
                    self.tsp_description = f"""خطاها:\n{enter.join([f'{item["message"]} (کد: {item["code"]})' for item in response_json['result']['data'][0]['data']['error']])}""" +\
                                            f"""\nهشدارها:\n{enter.join([f'{item["message"]} (کد: {item["code"]})' for item in response_json['result']['data'][0]['data']['warning']])}"""
                else:
                    raise exceptions.AccessError(str(response_json))


    def tsp_async(self, invoice_dictionary):
        self.tsp_check_constraints()

        invoice_json = json.dumps(invoice_dictionary).replace(" ", "")

        invoice_json_bytes = invoice_json.encode()
        symmetric_key_bytes = get_random_bytes(32)
        symmetric_key_padded_bytes = (symmetric_key_bytes * math.ceil(len(invoice_json_bytes) / len(symmetric_key_bytes)))[:len(invoice_json_bytes)]

        invoice_string_xor_bytes = bytearray()
        for i in range(len(symmetric_key_padded_bytes)):
            invoice_string_xor_bytes += bytearray([invoice_json_bytes[i] ^ symmetric_key_padded_bytes[i]])

        iv_bytes = get_random_bytes(16)
        aes_cipher = AES.new(symmetric_key_bytes, AES.MODE_GCM, iv_bytes)
        encrypted_invoice_string_xor_bytes, tag_bytes = aes_cipher.encrypt_and_digest(invoice_string_xor_bytes)
        encrypted_data_bytes = encrypted_invoice_string_xor_bytes + tag_bytes
        encoded_encrypted_data = base64.b64encode(encrypted_data_bytes)
        encrypted_data = encoded_encrypted_data.decode("utf8")

        SERVER_PUBLIC_KEY, SERVER_ENCRYPTION_KEY_ID = self.tsp_sync_get_server_info()
        oaep_cipher = PKCS1_OAEP.new(key=RSA.import_key(SERVER_PUBLIC_KEY), hashAlgo=SHA256, mgfunc=lambda x,y: pss.MGF1(x,y, SHA256))
        encrypted_symmetric_key_bytes = oaep_cipher.encrypt(symmetric_key_bytes.hex().encode())
        encoded_encrypted_symmetric_key = base64.b64encode(encrypted_symmetric_key_bytes)
        encrypted_symmetric_key = encoded_encrypted_symmetric_key.decode("utf8")

        UUID = str(uuid.uuid4())
        headers = {
            "requestTraceId": UUID,
            "timestamp": str(int(datetime.datetime.timestamp(datetime.datetime.now())*1000)),
            "Authorization": self.tsp_sync_get_token()
        }
        
        body = {
            "packets": [{
                "uid": UUID,
                "packetType": "INVOICE.V01",
                "retry": False,
                "data": encrypted_data,
                "encryptionKeyId": SERVER_ENCRYPTION_KEY_ID,
                "symmetricKey": encrypted_symmetric_key,
                "iv": iv_bytes.hex(),
                "fiscalId": self.company_id.tsp_unique_id,
                "dataSignature": self.tsp_get_signed_string(self.tsp_get_dictionary_normalized(invoice_dictionary))
            }],
        }

        body["signature"] = self.tsp_get_signed_string(self.tsp_get_dictionary_normalized({**body, **headers}))
        headers["Authorization"] = "Bearer " + headers["Authorization"]

        response = requests.post(SERVER_BASE_URL[self.company_id.tsp_server_mode] + "async/normal-enqueue", headers=headers, json=body)

        try:
            return response.json()
        except:
            raise exceptions.AccessError(_("TSP server is not reachable!"))


    def tsp_send(self):
        invoice_dictionary = self.tsp_get_invoice_dictionary()
        self.tsp_temp_taxid = invoice_dictionary["header"]["taxid"]
        if self.move_type == "out_invoice":
            invoice_dictionary["header"]["ins"] = 1
            invoice_dictionary["header"]["irtaxid"] = None
        elif self.move_type == "out_refund":
            invoice_dictionary["header"]["ins"] = 4
            invoice_dictionary["header"]["irtaxid"] = self.reversed_entry_id.tsp_taxid
        response_json = self.tsp_async(invoice_dictionary)
        _logger.info("TSP: " + str(response_json))
        self.tsp_reference_number = response_json["result"][0]["referenceNumber"]
        self.tsp_state = "pending_send"
        self.tsp_description = ""


    def tsp_edit(self):
        invoice_dictionary = self.tsp_get_invoice_dictionary()
        self.tsp_temp_taxid = invoice_dictionary["header"]["taxid"]
        invoice_dictionary["header"]["ins"] = 2
        invoice_dictionary["header"]["irtaxid"] = self.tsp_taxid
        response_json = self.tsp_async(invoice_dictionary)
        _logger.info("TSP: " + str(response_json))
        self.tsp_reference_number = response_json["result"][0]["referenceNumber"]
        self.tsp_state = "pending_edit"
        self.tsp_description = ""


    def tsp_cancel(self):
        invoice_dictionary = self.tsp_get_invoice_dictionary()
        self.tsp_temp_taxid = invoice_dictionary["header"]["taxid"]
        invoice_dictionary["header"]["ins"] = 3
        invoice_dictionary["header"]["irtaxid"] = self.tsp_taxid
        response_json = self.tsp_async(invoice_dictionary)
        _logger.info("TSP: " + str(response_json))
        self.tsp_reference_number = response_json["result"][0]["referenceNumber"]
        self.tsp_state = "pending_cancel"
        self.tsp_description = ""