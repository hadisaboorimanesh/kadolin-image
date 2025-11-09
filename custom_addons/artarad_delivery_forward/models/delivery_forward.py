# -*- coding: utf-8 -*-
import json
import time
import unicodedata
from datetime import datetime, timedelta

import requests
import jdatetime

from odoo import models, fields, api, _
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


# شروع هر شیفت (ساعت روز)
SHIFT_START = {1: 9, 2: 12, 3: 15, 4: 18}
MIN_BUFFER_HOURS = 6  # قانون فوروارد

def _to_local(rec, dt_utc):
    return fields.Datetime.context_timestamp(rec, dt_utc)

def _jalali(date_obj):  # date -> "YYYY/MM/DD"
    return jdatetime.date.fromgregorian(date=date_obj).strftime("%Y/%m/%d")

def _guess_shift_by_hour(hour):
    if 9 <= hour < 12:  return 1
    if 12 <= hour < 15: return 2
    if 15 <= hour < 18: return 3
    if 18 <= hour < 21: return 4
    return 1  # خارج از بازه‌ها

def compute_forward_pickup_and_delivery(picking, carrier):
    """برمی‌گرداند: (pickup_date_j, pickup_shift, delivery_date_j, delivery_shift) — همهٔ فیلدها پر می‌شوند."""
    now_local = fields.Datetime.context_timestamp(picking, fields.Datetime.now())
    base_utc = picking.sale_id.select_deliver_date

    scheduled_date = picking.scheduled_date or fields.Datetime.now()
    # base_local = _to_local(picking, base_utc)

    # اگر روی carrier شیفت پیش‌فرض داری، از همان شروع کن وگرنه بر اساس ساعت فعلی حدس بزن
    # start_shift = int(getattr(carrier, "forward_pickup_shift", 0) or 0) or _guess_shift_by_hour(base_local.hour)
    if base_utc:
      day_local = base_utc
    else:
      day_local = base_utc.date()
    # shift = start_shift

    # پیدا کردن نزدیک‌ترین شیفت معتبر با بافر ۶ ساعت
    # while True:
    #     shift_start_dt = datetime(
    #         year=day_local.year, month=day_local.month, day=day_local.day,
    #         hour=SHIFT_START[shift], minute=0, second=0, tzinfo=now_local.tzinfo
    #     )
    #     ref_dt = max(now_local, base_local)
    #     if shift_start_dt - ref_dt >= timedelta(hours=MIN_BUFFER_HOURS):
    #         pickup_date_j = _jalali(shift_start_dt.date())
    #         pickup_shift = shift
    #         break
    #     if shift < 4:
    #         shift += 1
    #     else:
    #         day_local = day_local + timedelta(days=1)
    #         shift = 1
    #
    # # تحویل اجباری: اگر pickup شیفت 1/2 باشد => همان روز شیفت بعدی؛ اگر 3/4 => فردا شیفت 2
    # if pickup_shift in (1, 2):
    #     delivery_day = day_local
    #     delivery_shift = pickup_shift + 1
    # else:
    #     delivery_day = day_local + timedelta(days=1)
    #     delivery_shift = 2
    pickup_shift =1 if  picking.sale_id.select_deliver_date=='morning' else 2
    delivery_shift = pickup_shift
    delivery_date_j = _jalali(day_local)
    pickup_date_j = _jalali(day_local- timedelta(days=1))
    return pickup_date_j, int(pickup_shift), delivery_date_j, int(delivery_shift)


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(
        selection_add=[("forward", "Forward")],
        ondelete={'forward': 'set default'},
    )

    # تنظیمات Forward
    forward_base_url = fields.Char(string="Forward Base URL")   # مثال: https://api.forward.ir
    forward_username = fields.Char(string="Forward Username")
    forward_password = fields.Char(string="Forward Password")

    # پارامترهای بیزینسی پیش‌فرض
    forward_sender_address_id = fields.Char(string="Sender Address ID")
    forward_box_size = fields.Integer(string="Default Box Size", default=1)
    forward_box_content_id = fields.Integer(string="Default Box Content ID", default=501)

    # کش محلی (اختیاری برای نمایش/دیباگ)
    forward_token_cached_at = fields.Float(readonly=True)
    forward_token_ttl = fields.Integer(string="Token TTL (sec)", default=86000)
    forward_token_value = fields.Char(readonly=True)

    def _get_token(self, carrier):
        ICP = self.env['ir.config_parameter'].sudo()
        key_val = f"artarad_forward.token.{carrier.id}.value"
        key_ts = f"artarad_forward.token.{carrier.id}.ts"
        key_ttl = f"artarad_forward.token.{carrier.id}.ttl"

        # کش معتبر؟
        val = ICP.get_param(key_val)
        ts = float(ICP.get_param(key_ts) or 0)
        ttl = int(ICP.get_param(key_ttl) or carrier.forward_token_ttl or 86000)
        now = time.time()
        if val and (now - ts) < ttl:
            return val

        # درخواست توکن جدید
        base = (carrier.forward_base_url or "").rstrip("/")
        url = f"{base}/identity/v2/login"
        body = {
            "username": carrier.forward_username or "",
            "password": carrier.forward_password or "",
        }
        if not body["username"] or not body["password"] or not base:
            raise UserError(_("Forward: Missing base URL/username/password."))

        res = requests.post(url, headers={"Content-Type": "application/json"},
                            data=json.dumps(body), timeout=25)
        if res.status_code != 200:
            raise UserError(_("Forward: token failed (%s) -> %s") % (res.status_code, res.text))
        try:
            data = res.json()
            token = data.get("accessToken")
        except Exception:
            raise UserError(_("Forward: token invalid JSON: %s") % res.text)
        if not token:
            raise UserError(_("Forward: no token in response"))

        # ذخیره کش
        ICP.set_param(key_val, token)
        ICP.set_param(key_ts, str(now))
        ICP.set_param(key_ttl, str(ttl))
        return token

    def _api_post(self, carrier, path, payload):
        base = (carrier.forward_base_url or "").rstrip("/")
        token = self._get_token(carrier)
        url = f"{base}{path}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        # API شما در پی‌اچ‌پی: status 200 => ok
        if res.status_code != 200:
            raise UserError(_("Forward POST %s failed: %s") % (path, res.text))
        try:
            return res.json()
        except Exception:
            raise UserError(_("Forward POST invalid JSON: %s") % res.text)

    def forward_cancel_shipment(self, picking):
        """Cancel by code = carrier_tracking_ref -> POST /order/v2/Cancel"""
        if not picking.carrier_id or picking.carrier_id.delivery_type != "forward":
            return False
        code = picking.carrier_tracking_ref
        if not code:
            picking.message_post(body=_("Forward: No code to cancel."))
            return False
        payload = {"code": code}
        try:
            resp = self._api_post(picking.carrier_id, "/order/v2/Cancel", payload)
        except Exception as e:
            picking.message_post(body=_("Forward Cancel: HTTP error: %s") % e)
            return False

        # اگر API در status 200 جواب عادی می‌دهد فرض می‌کنیم کنسل شد
        picking.message_post(body=_("Forward: Shipment %s cancelled.") % code)
        picking.sudo().write({"carrier_tracking_ref": False,
                              "carrier_tracking_code":False})
        return True



@register_carrier("forward", "delivery.adapter.forward")
class DeliveryAdapterForward(models.AbstractModel):
    _name = "delivery.adapter.forward"
    _description = "Forward Carrier Adapter"



    # ---------- Utils ----------
    def _norm(self, s):
        if not s:
            return ""
        s = ''.join(ch for ch in str(s) if unicodedata.category(ch) != 'Cf')
        return unicodedata.normalize('NFKC', s).strip()

    # ---------- Token ----------
    def _get_token(self, carrier: DeliveryCarrier):
        ICP = self.env['ir.config_parameter'].sudo()
        key_val = f"artarad_forward.token.{carrier.id}.value"
        key_ts = f"artarad_forward.token.{carrier.id}.ts"
        key_ttl = f"artarad_forward.token.{carrier.id}.ttl"

        # کش معتبر؟
        val = ICP.get_param(key_val)
        ts = float(ICP.get_param(key_ts) or 0)
        ttl = int(ICP.get_param(key_ttl) or carrier.forward_token_ttl or 86000)
        now = time.time()
        if val and (now - ts) < ttl:
            return val

        # درخواست توکن جدید
        base = (carrier.forward_base_url or "").rstrip("/")
        url = f"{base}/identity/v2/login"
        body = {
            "username": carrier.forward_username or "",
            "password": carrier.forward_password or "",
        }
        if not body["username"] or not body["password"] or not base:
            raise UserError(_("Forward: Missing base URL/username/password."))

        res = requests.post(url, headers={"Content-Type": "application/json"},
                            data=json.dumps(body), timeout=25)
        if res.status_code != 200:
            raise UserError(_("Forward: token failed (%s) -> %s") % (res.status_code, res.text))
        try:
            data = res.json()
            token = data.get("accessToken")
        except Exception:
            raise UserError(_("Forward: token invalid JSON: %s") % res.text)
        if not token:
            raise UserError(_("Forward: no token in response"))

        # ذخیره کش
        ICP.set_param(key_val, token)
        ICP.set_param(key_ts, str(now))
        ICP.set_param(key_ttl, str(ttl))
        return token

    def _api_get(self, carrier, path, params=None):
        base = (carrier.forward_base_url or "").rstrip("/")
        token = self._get_token(carrier)
        url = f"{base}{path}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        res = requests.get(url, headers=headers, params=params, timeout=25)
        if res.status_code != 200:
            raise UserError(_("Forward GET %s failed: %s") % (path, res.text))
        try:
            return res.json()
        except Exception:
            raise UserError(_("Forward GET invalid JSON: %s") % res.text)

    def _api_post(self, carrier, path, payload):
        base = (carrier.forward_base_url or "").rstrip("/")
        token = self._get_token(carrier)
        url = f"{base}{path}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        # API شما در پی‌اچ‌پی: status 200 => ok
        if res.status_code != 200:
            raise UserError(_("Forward POST %s failed: %s") % (path, res.text))
        try:
            return res.json()
        except Exception:
            raise UserError(_("Forward POST invalid JSON: %s") % res.text)

    # ---------- Province/City caches ----------
    def _get_provinces(self, carrier):
        ICP = self.env['ir.config_parameter'].sudo()
        key = "artarad_forward.provinces"
        cached = ICP.get_param(key)
        if cached:
            try:
                data = json.loads(cached)
                if isinstance(data, dict) and data:
                    return data
            except Exception:
                pass
        # GET /param/v2/province
        data = self._api_get(carrier, "/param/v2/province")
        # انتظار: لیست [{id, title}, ...]
        prov_map = {}
        if isinstance(data, list):
            for it in data:
                pid = it.get("id")
                title = self._norm(it.get("title"))
                if pid and title:
                    prov_map[str(pid)] = title
        if prov_map:
            ICP.set_param(key, json.dumps(prov_map, ensure_ascii=False))
        return prov_map

    def _get_cities_in_province(self, carrier, province_id):
        ICP = self.env['ir.config_parameter'].sudo()
        key = f"artarad_forward.cities.{province_id}"
        cached = ICP.get_param(key)
        if cached:
            try:
                data = json.loads(cached)
                if isinstance(data, list) and data:
                    return data
            except Exception:
                pass
        # GET /param/v2/city?provinceId=#
        data = self._api_get(carrier, "/param/v2/city", params={"provinceId": province_id})
        # انتظار: لیست [{id, title}, ...]
        cities = []
        if isinstance(data, list):
            for it in data:
                cid = it.get("id")
                title = self._norm(it.get("title"))
                if cid and title:
                    cities.append({"id": cid, "title": title, "province_id": province_id})
        if cities:
            ICP.set_param(key, json.dumps(cities, ensure_ascii=False))
        return cities

    def _find_province_id(self, carrier, province_title):
        norm = self._norm(province_title)
        if not norm:
            return None
        prov_map = self._get_provinces(carrier)
        # exact
        for pid, title in prov_map.items():
            if title == norm:
                return int(pid)
        # fuzzy کوچک
        import difflib
        matches = difflib.get_close_matches(norm, list(prov_map.values()), n=1, cutoff=0.7)
        if matches:
            m = matches[0]
            for pid, title in prov_map.items():
                if title == m:
                    return int(pid)
        return None

    def _find_city_id(self, carrier, province_id, city_title):
        norm = self._norm(city_title)
        if not norm or not province_id:
            return None
        cities = self._get_cities_in_province(carrier, province_id)
        for it in cities:
            if it["province_id"] == province_id and it["title"] == norm:
                return int(it["id"])
        import difflib
        matches = difflib.get_close_matches(norm, [c["title"] for c in cities], n=1, cutoff=0.7)
        if matches:
            m = matches[0]
            for it in cities:
                if it["title"] == m:
                    return int(it["id"])
        return None

    # ---------- Send / Cancel ----------
    @api.model
    def send_for_picking(self, carrier, picking):
        """Build Forward order from picking and send /order/v2/Insert"""
        if not carrier or carrier.delivery_type != "forward":
            return False

        if not picking._is_pack():
            return False

        if picking.carrier_tracking_ref:
            return True

        # آدرس گیرنده
        partner = picking.partner_id or picking.sale_id.partner_shipping_id or picking.partner_id
        if not partner:
            picking.message_post(body=_("Forward: Missing partner on picking."))
            return False

        # استان/شهر مقصد
        province_id = self._find_province_id(carrier, partner.state_id.name if partner.state_id else "")
        if not province_id:
            picking.message_post(body=_("Forward: Province not found for '%s'.") % (partner.state_id.name if partner.state_id else "-"))
            return False

        city_id = self._find_city_id(carrier, province_id, partner.city)
        if not city_id:
            picking.message_post(body=_("Forward: City '%s' not found in province id %s.") % (partner.city or "-", province_id))
            return False

        # مبالغ/ابعاد
        # boxPriceValue: نمونه ساده — اگر منطق دیگری داری جایگزین کن
        box_price_value = int(round((picking.sale_id.amount_total if picking.sale_id else 0.0) * 10))  # ریال
        sender_address_id = int(carrier.forward_sender_address_id or 0)
        # if not sender_address_id:
        #     picking.message_post(body=_("Forward: 'Sender Address ID' is required on carrier."))
        #     return False

        # زمان‌بندی (اختیاری: اگر داری از context یا تنظیمات بخوان)
        base_dt_local = fields.Datetime.context_timestamp(
            picking, picking.scheduled_date or fields.Datetime.now()
        )

        pickup_date, pickup_shift, delivery_date, delivery_shift = compute_forward_pickup_and_delivery(picking, carrier)

        # مختصات (اگر داری)
        receiver_location = None
        if getattr(partner, "partner_latitude", False) and getattr(partner, "partner_longitude", False):
            receiver_location = f"{partner.partner_latitude}, {partner.partner_longitude}"

        payload = {
            "orders": [{
                "orderId": picking.origin,                       # معادل increment_id
                "boxPriceValue": box_price_value,             # ریال
                "senderAddressId": sender_address_id,
                "receiverProvinceId": province_id,
                "receiverCityId": city_id,
                "receiverTitle": partner.display_name or (partner.name or ""),
                # "receiverPhone": partner.mobile or partner.phone or "",
                "receiverPhone": "09359724338",
                "receiverAddress": partner.contact_address_complete or partner.street or "",
                "receiverLocation": receiver_location,
                "receiverPostalCode": partner.zip or None,
                "boxSize": int(carrier.forward_box_size or 1),
                "pickupDate": pickup_date,
                "pickupShift": pickup_shift,
                "deliveryDate": delivery_date,
                "deliveryShift": delivery_shift,
                "boxContentId": int(carrier.forward_box_content_id or 501),
            }]
        }

        try:
            resp = self._api_post(carrier, "/order/v2/Insert", payload)
        except Exception as e:
            picking.message_post(body=_("Forward: HTTP error: %s") % e)
            return False

        # انتظار بر اساس PHP: response['message']->orders and each has code, orderId, ...
        orders = (resp or {}).get("orders") or ( (resp or {}).get("message") or {} ).get("orders") or []
        if not orders:
            # بعضی سرورها: کل پاسخ زیر message می‌آید
            picking.message_post(body=_("Forward: Empty orders in response: %s") % json.dumps(resp, ensure_ascii=False))
            return False

        first = orders[0]
        code = first.get("code")
        if not code:
            picking.message_post(body=_("Forward: No 'code' in insert response: %s") % json.dumps(first, ensure_ascii=False))
            return False

        picking.sudo().write({"carrier_tracking_ref": code,
                              'carrier_tracking_code':code})
        picking.message_post(body=_("Forward: Code created: <b>%s</b> (orderId=%s)") % (code, first.get("orderId")))
        return True



