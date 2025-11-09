import json
import logging
import requests

from odoo import models, _
from odoo.exceptions import UserError

try:
    # اگر decorator رجیستری در بیس‌تان هست
    from odoo.addons.artarad_delivery_base.models.delivery_base import register_carrier
except Exception:
    def register_carrier(code, model_name):
        def _decorator(cls):
            cls._carrier_code = code
            cls._carrier_model_ref = model_name
            return cls
        return _decorator

_logger = logging.getLogger(__name__)

@register_carrier("post", model_name="delivery.adapter.post")
class DeliveryAdapterPost(models.AbstractModel):
    _name = "delivery.adapter.post"
    _description = "Iran Post Adapter"

    def _endpoint(self, carrier, path):
        base = (carrier.post_base_url or "").rstrip("/")
        return f"{base}{path}"

    def _build_payload(self, carrier, picking):
        partner = picking.partner_id.commercial_partner_id

        if not carrier.post_contract_code or not carrier.post_username or not carrier.post_password:
            raise UserError(_("Post carrier credentials are not set (contract/user/pass)."))

        if not carrier.post_source_city_code:
            raise UserError(_("Post source city code (sourcecode) is not set on carrier."))

        if not partner.post_city_code:
            raise UserError(_("Post destination city code (destcode) is not set on the customer (partner)."))

        if not partner.zip:
            raise UserError(_("Receiver postal code is required (partner.zip)."))
        if not picking._is_pack():
            return False

        # نام‌ها و موبایل/شناسه
        sender_name = carrier.post_sender_name or (self.env.company.name or "Sender")
        sender_postal = carrier.post_sender_postalcode or (self.env.company.zip or "")
        sender_addr = carrier.post_sender_address or (self.env.company.contact_address or "")
        sender_mobile = carrier.post_sender_mobile or (self.env.company.phone or "")
        sender_national = carrier.post_sender_national_id or ""

        receiver_name = partner.name or "Receiver"
        receiver_mobile = partner.mobile or partner.phone or ""
        receiver_national = partner.national_id or partner.vat or ""
        receiver_addr = picking.partner_id._get_contact_address() or partner.contact_address or ""
        receiver_postal = partner.zip

        # وزن؛ اگر وزن خط نباشه 100 گرم حداقل
        weight_gram = 0
        try:
            # اگر وزن رزرو شده/محاسبه شده داری، همونو بردار؛ وگرنه sum move_lines
            weight_gram = int(round(1000 * (picking.weight or 0.0)))
        except Exception:
            pass
        if weight_gram <= 0:
            weight_gram = 100  # حداقل

        payload = {
            "contractcode": carrier.post_contract_code,
            "username": carrier.post_username,
            "password": carrier.post_password,

            "postnodecode": carrier.post_postnodecode or "",

            "typecode": int(carrier.post_typecode or 11),
            "servicetype": int(carrier.post_servicetype or 1),
            "parceltype": int(carrier.post_parceltype or 2),

            "sourcecode": int(carrier.post_source_city_code),
            "destcode": int(partner.post_city_code),

            "sendername": sender_name,
            "receivername": receiver_name,

            "receiverpostalcode": str(receiver_postal or ""),
            "senderpostalcode": str(sender_postal or ""),

            "weight": int(weight_gram),

            "postalcostcategoryid": int(carrier.post_postalcostcategoryid or 1),
            "postalcosttypeflag": (carrier.post_postalcosttypeflag or "F").lower(),

            "relationalkey": picking.name or "",

            "senderid": str(sender_national or ""),
            "receiverid": str(receiver_national or ""),

            "sendermobile": str(sender_mobile or ""),
            "receivermobile": str(receiver_mobile or ""),

            "senderaddress": sender_addr or "",
            "receiveraddress": receiver_addr or "",

            "insurancetype": int(carrier.post_insurancetype or 1),
            "insuranceamount": int(carrier.post_insuranceamount or 0),

            "spsdestinationtype": int(carrier.post_spsdestinationtype or 0),
            "spsreceivertimetype": int(carrier.post_spsreceivertimetype or 0),
            "spsparceltype": int(carrier.post_spsparceltype or 0),

            "tlsservicetype": int(carrier.post_tlsservicetype or 0),

            "tworeceiptant": bool(carrier.post_tworeceiptant),
            "electroreceiptant": bool(carrier.post_electroreceiptant),

            "iscot": bool(carrier.post_iscot),
            "smsservice": bool(carrier.post_smsservice),
            "isnonstandard": bool(carrier.post_isnonstandard),

            "sendplacetype": int(carrier.post_sendplacetype or 2),

            "Contractorportion": int(carrier.post_contractorportion or 0),
            "Contetnts": carrier.post_contents or "",

            "Vid": picking.name or "",
            "boxsize": int(carrier.post_boxsize or 6),
        }
        return payload

    def _api_post(self, carrier, path, payload: dict):
        url = self._endpoint(carrier, path)
        headers = {"Content-Type": "application/json"}
        body = json.dumps(payload, ensure_ascii=False)
        _logger.info("POST %s payload=%s", url, body)
        try:
            resp = requests.post(url, headers=headers, data=body, timeout=30)
        except Exception as e:
            raise UserError(_("Post request failed: %s") % e)

        if resp.status_code != 200:
            raise UserError(_("Post POST %s failed: %s") % (path, resp.text))
        try:
            data = resp.json()
        except Exception:
            raise UserError(_("Post invalid JSON response: %s") % resp.text)
        return data

    def send_for_picking(self, carrier, picking):
        payload = self._build_payload(carrier, picking)
        data = self._api_post(carrier, "/barcode/getbarcode", payload)
        status = data.get("Status")
        if status not in (True, "true", 1, "1"):
            msg = data.get("Message") or "Post error"
            raise UserError(_("Post failed: %s") % msg)

        barcode = data.get("Barcode")
        if not barcode:
            raise UserError(_("Post returned no Barcode."))

        self.env["delivery.carrier.log"].sudo().create({
            "picking_id": picking.id,
            "carrier_id": carrier.id,
            "status": "success",
            "response_text": json.dumps(data, ensure_ascii=False),
        })

        return barcode