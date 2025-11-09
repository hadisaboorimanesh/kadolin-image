# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import requests
from datetime import date

# اگر قبلاً decorator ثبت حامل را داری، می‌توانی ازش استفاده کنی.
# در غیر اینصورت، این no-op decorator را نگه‌دار تا کلاس رجیستر شود.
try:
    from odoo.addons.artarad_delivery_base.models.delivery_base import register_carrier
except Exception:
    def register_carrier(code, model_name):
        def _decorator(cls):
            cls._carrier_code = code
            cls._carrier_model_ref = model_name
            return cls
        return _decorator


# --------------------------
# فیلدهای تنظیمات چاپار روی delivery.carrier
# (اگر قبلاً اضافه کرده‌ای، این کلاس را حذف کن)
# --------------------------
class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    # نوع جدید حامل
    delivery_type = fields.Selection(
        selection_add=[('chapar', 'Chapar')],
        ondelete={'chapar': 'set default'},
    )
    # کرنشیال‌ها و فرستنده
    chapar_username = fields.Char("Chapar Username")
    chapar_password = fields.Char("Chapar Password")
    chapar_sender_city = fields.Char("Sender City No")
    chapar_sender_person = fields.Char("Sender Person")
    chapar_sender_company = fields.Char("Sender Company")
    chapar_sender_telephone = fields.Char("Sender Telephone")
    chapar_sender_mobile = fields.Char("Sender Mobile")
    chapar_sender_email = fields.Char("Sender Email")
    chapar_sender_address = fields.Char("Sender Address")
    chapar_sender_postcode = fields.Char("Sender Postcode")

    def _chapar_call(self, url, data_dict, timeout=25):
        """ POST به سرویس چاپار؛ بدنه به صورت فرم با کلید input (JSON) """
        body = json.dumps(data_dict, ensure_ascii=False)
        res = requests.post(url, data={'input': body}, timeout=timeout)
        res.raise_for_status()
        try:
            return res.json()
        except Exception:
            return {'result': 0, 'message': 'Invalid JSON response', 'raw': res.text}

    def chapar_cancel_shipment(self,picking):
        """
        لغو مرسوله در چاپار با استفاده از tracking code
        """
        reason = "انصراف از ارسال"
        if picking.carrier_id.delivery_type != "chapar":
            return False
        tracking = picking.carrier_tracking_ref
        if not tracking:
            picking.message_post(body=_("Chapar: No tracking to cancel."))
            return False

        username = picking.carrier_id.chapar_username
        password = picking.carrier_id.chapar_password
        if not username or not password:
            picking.message_post(body=_("Chapar: Missing credentials for cancellation."))
            return False

        payload = {
            'user': {'username': username, 'password': password},
            'consignment_no': str(tracking),
            'reason': reason,
        }

        try:
            resp = self._chapar_call("https://app.krch.ir/v1/cancel_pickup", payload)
        except Exception as e:
            picking.message_post(body=_("Chapar Cancel: HTTP error: %s") % e)
            return False

        if not isinstance(resp, dict) or int(resp.get('result', 0)) != 1:
            msg = (resp or {}).get('message', 'Unknown error') if isinstance(resp, dict) else str(resp)
            picking.message_post(body=_("Chapar Cancel: API error: %s") % msg)
            return False

        picking.message_post(body=_("Chapar: Shipment %s cancelled successfully.") % tracking)
        picking.sudo().write({'carrier_tracking_ref': False,
                              'carrier_tracking_code':False})
        return True



# --------------------------
# Adapter چاپار
# --------------------------
@register_carrier("chapar", "delivery.adapter.chapar")
class DeliveryAdapterChapar(models.AbstractModel):
    _name = "delivery.adapter.chapar"
    _description = "Chapar Carrier Adapter"

    # API call helper
    def _chapar_call(self, url, data_dict, timeout=25):
        """ POST به سرویس چاپار؛ بدنه به صورت فرم با کلید input (JSON) """
        body = json.dumps(data_dict, ensure_ascii=False)
        res = requests.post(url, data={'input': body}, timeout=timeout)
        res.raise_for_status()
        try:
            return res.json()
        except Exception:
            return {'result': 0, 'message': 'Invalid JSON response', 'raw': res.text}

    # کش شهرها
    def _chapar_get_city_map(self):
        ICP = self.env['ir.config_parameter'].sudo()
        cached = ICP.get_param('artarad_delivery_chapar.city_map')
        if cached:
            try:
                data = json.loads(cached)
                if isinstance(data, dict) and data:
                    return data
            except Exception:
                pass
        # دریافت تازه
        payload = {'state': {'no': 0}}
        resp = self._chapar_call("https://app.krch.ir/v1/get_city", payload)
        mapping = {}
        try:
            cities = (resp.get('objects') or {}).get('city') or []
            for item in cities:
                mapping[str(item.get('no'))] = item.get('name')
        except Exception:
            mapping = {}
        if mapping:
            ICP.set_param('artarad_delivery_chapar.city_map', json.dumps(mapping, ensure_ascii=False))
        return mapping

    def _chapar_find_city_no(self, city_name):
        """ بر اساس نام فارسی شهر، کد چاپار را برگردان (یا None) """
        city_map = self._chapar_get_city_map()
        if not city_name:
            return None
        for no, name in city_map.items():
            if (name or '').strip() == (city_name or '').strip():
                try:
                    return int(no)
                except Exception:
                    return None
        return None

    def _chapar_suggest_cities(self, city_name: str, top=3):
        """Return up to `top` closest matches from Chapar city list for user feedback."""
        import difflib, unicodedata
        def _norm(s):
            if not s:
                return ""
            s = ''.join(ch for ch in str(s) if unicodedata.category(ch) != 'Cf')
            return unicodedata.normalize('NFKC', s).strip()
        mapping = self._chapar_get_city_map()
        names = list(mapping.values())
        q = _norm(city_name)
        if not names or not q:
            return []
        return difflib.get_close_matches(q, names, n=top, cutoff=0.6)

    # ساخت و ارسال سفارش
    @api.model
    def send_for_picking(self, carrier, picking):

        if not carrier or carrier.delivery_type != "chapar":
            return False
        if not picking._is_pack():
            return False

        if picking.carrier_tracking_ref:
            return True

        # کرنشیال‌ها
        username = carrier.chapar_username
        password = carrier.chapar_password
        if not username or not password:
            picking.message_post(body=_("Chapar: Missing username/password on carrier."))
            return False

        partner = picking.partner_id or picking.sale_id.partner_shipping_id or picking.partner_id
        if not partner:
            picking.message_post(body=_("Chapar: Missing partner on picking."))
            return False

        recv_city = (partner.city or "").strip()
        city_no = self._chapar_find_city_no(recv_city)
        if city_no is None:
            # تلاش برای پیشنهاد نزدیک‌ترین شهرها
            suggestions = self._chapar_suggest_cities(recv_city)
            if suggestions:
                picking.message_post(body=_("Chapar: City '%s' not found. Did you mean: %s ?") % (recv_city or "-", ", ".join(suggestions)))
            else:
                picking.message_post(body=_("Chapar: City '%s' not found in Chapar list.") % (recv_city or "-"))
            return False
        sender_city_no = self._chapar_find_city_no(carrier.chapar_sender_city)
        if sender_city_no is None:
            # تلاش برای پیشنهاد نزدیک‌ترین شهرها
            suggestions = self._chapar_suggest_cities(carrier.chapar_sender_city)
            if suggestions:
                picking.message_post(body=_("Chapar: City '%s' not found. Did you mean: %s ?") % (carrier.chapar_sender_city or "-",
                                                                                                  ", ".join(
                                                                                                      suggestions)))
            else:
                picking.message_post(body=_("Chapar: City '%s' not found in Chapar list.") % (carrier.chapar_sender_city or "-"))
            return False

        # فرستنده از روی carrier
        sender = {
            'person': carrier.chapar_sender_person or '',
            'company': carrier.chapar_sender_company or '',
            'city_no': sender_city_no,
            'telephone': carrier.chapar_sender_telephone or '',
            'mobile': carrier.chapar_sender_mobile or '',
            'email': carrier.chapar_sender_email or '',
            'address': carrier.chapar_sender_address or '',
            'postcode': carrier.chapar_sender_postcode or '1111111111',
        }
        if not sender['city_no']:
            picking.message_post(body=_("Chapar: 'Sender City No' is required on the carrier."))
            return False

        phone = partner.mobile or partner.phone or ''
        receiver = {
            'person': partner.display_name or (partner.name or ''),
            'company': partner.parent_id.name if partner.parent_id else '',
            'city_no': city_no,
            'telephone': phone,
            'mobile': phone,
            'email': partner.email or '',
            'address': partner.contact_address_complete or partner.street or '',
            'postcode': partner.zip or '1111111111',
        }

        reference = picking.origin or '-'
        service = 35 if recv_city == 'تهران' else 1
        weight =1
        value = 0

        cn = {
            'reference': reference,
            'date': date.today().isoformat(),
            'assinged_pieces': 1,
            'service': service,
            'value': value,
            'payment_term': 0,
            'weight': weight,
            'content': _('Goods'),
        }

        payload = {
            'user': {'username': username, 'password': password},
            'bulk': [{'cn': cn, 'sender': sender, 'receiver': receiver}],
        }

        try:
            resp = self._chapar_call("https://app.krch.ir/v1/bulk_import", payload)
        except Exception as e:
            picking.message_post(body=_("Chapar: HTTP error: %s") % e)
            return False

        if not isinstance(resp, dict) or int(resp.get('result', 0)) != 1:
            msg = (resp or {}).get('message', 'Unknown error') if isinstance(resp, dict) else str(resp)
            picking.message_post(body=_("Chapar: API error: %s") % msg)
            return False

        result_list = (resp.get('objects') or {}).get('result') or []
        if not result_list:
            picking.message_post(body=_("Chapar: Empty result list from API."))
            return False

        # طبق بازخورد شما: reference = شماره بارنامه، package[0] = شماره رهگیری
        item = result_list[0]
        consignment_no = item.get('tracking')  # شماره بارنامه (برای کنسل لازم داریم)
        tracking_code = (item.get('package') or [None])[0]  # شماره رهگیری

        if not consignment_no:
            picking.message_post(body=_("Chapar: Missing consignment number in response."))
            return False

        # ذخیره‌ی بارنامه در فیلد ترکینگ
        picking.sudo().write({'carrier_tracking_ref': consignment_no,
                              'carrier_tracking_code':tracking_code})

        # لاگِ دوستانه: هر دو مقدار را نمایش بده
        msg = _("Chapar: Consignment created.<br/>"
                "<b>Consignment (بارنامه):</b> %s<br/>"
                "<b>Tracking (رهگیری):</b> %s") % (consignment_no, tracking_code or '-')
        picking.message_post(body=msg)

        return True

