# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import requests

NESCHAN_BASE = "https://api.neshan.org"
EP_REVERSE = "/v5/reverse"   # بسته به پلن شما ممکن است متفاوت باشد (مستند نشان را چک کنید)


def _api_key_server():
    return "service.d7fc1d8fe8ea4fe3b05007cb6a32b482"
        # request.env["ir.config_parameter"].sudo().get_param("neshan.api_key", ""))

def _headers():
    return {"Api-Key": _api_key_server()}

def _clean_float(val):
    if val is None: return None
    s = str(val).strip().replace("٬", "").replace(",", ".")
    try: return float(s)
    except: return None

class NeshanProxy(http.Controller):

    @http.route("/neshan/reverse", type="json", auth="public", website=True, csrf=False)
    def reverse(self, lat=None, lng=None, lang="fa"):
        """Proxy امن برای Reverse Geocoding نشان؛ نتیجهٔ ساده‌شده برمی‌گرداند."""
        lat = _clean_float(lat)
        lng = _clean_float(lng)
        if lat is None or lng is None:
            return {"ok": False, "error": "invalid_lat_lng"}

        key = _api_key_server()
        if not key:
            return {"ok": False, "error": "no_server_key"}

        try:
            r = requests.get(
                NESCHAN_BASE + EP_REVERSE,
                params={"lat": lat, "lng": lng, "lang": lang},
                headers=_headers(),
                timeout=5,
            )
            if r.status_code != 200:
                return {"ok": False, "status": r.status_code, "error": "upstream_error"}
            data = r.json() or {}
        except Exception as e:
            return {"ok": False, "error": "request_failed", "detail": str(e)}

        # این بخش را با ساختار واقعی پاسخ نشان هماهنگ کنید:
        address = data.get("formatted_address") or data.get("address") or ""
        comps = data.get("address_components") or {}
        city  = comps.get("city") or data.get("city") or ""
        state = comps.get("state") or comps.get("province") or data.get("state") or ""
        dist  = comps.get("district") or comps.get("neighbourhood") or ""
        zipc  = comps.get("postal_code") or data.get("postal_code") or ""

        return {
            "ok": True,
            "result": {
                "address": address,
                "city": city,
                "state": state,
                "district": dist,
                "postal_code": zipc,
                "lat": lat,
                "lng": lng,
            }
        }