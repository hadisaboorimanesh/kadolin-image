# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, date, timedelta, timezone
import jdatetime

import json
import requests


_logger = logging.getLogger(__name__)

# رجیستر کردن carrier جدید داخل رجیستری بیس
from odoo.addons.artarad_delivery_base.models.delivery_base import register_carrier

TAROFF_DEFAULT_BASE = "https://api.taroffexpress.com/api"  # از PDF


def _to_jdate_str(dt):
    if not dt:
        return None
    if not jdatetime:
        raise UserError(_("Python package 'jdatetime' is required for Taroff date formatting."))
    if isinstance(dt, datetime):
       jd = jdatetime.datetime.fromgregorian(datetime=dt)
    if isinstance(dt, date):
       jd = jdatetime.datetime.fromgregorian(date=dt)
    return jd.strftime("%Y/%m/%d")

class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"


    delivery_type = fields.Selection(selection_add=[("taroff", "TAROFF")],ondelete={'taroff': 'set default'},)

    taroff_base_url = fields.Char(
        string="Taroff Base URL",
        default=TAROFF_DEFAULT_BASE,
        help="e.g. https://api.taroffexpress.com/api",
    )
    taroff_api_key = fields.Char(string="Taroff API Key", help="customer key / api key")
    taroff_default_shift = fields.Selection(
        selection=[("1", "صبح"), ("2", "بعدازظهر")],
        string="Default Pickup Shift",
        default="1",
        help="If scheduled time cannot decide, use this.",
    )
    taroff_default_order_type = fields.Selection(
        [("1", "تبعیع/یک مرسوله"), ("0", "تعددس/بچ")]
        , string="Order Type", default="1"
    )
    taroff_use_mobile_as_phone = fields.Boolean(
        string="Use Mobile As Phone", default=True,
        help="If receiver has mobile, use it for both phone & cell"
    )
    taroff_default_packing = fields.Char(string="Default Packing", help="اختیاری: نوع بسته‌بندی")
    taroff_default_vol = fields.Selection([("0","بدون حجم غیرمتعارف"),("1","حجم‌دار")],
                                          string="Vol Flag", default="0")
    taroff_cod = fields.Selection([("0","بدون COD"),("1","COD دریافت مقصد")],
                                  string="COD", default="0")
    taroff_sender_wh_code = fields.Char(string="Warehouse Code (whcode)",
                                        help="کد انبار ثبت‌شده در Taroff (اختیاری)")

    def taroff_cancel_shipment(self, picking):
        if not picking.carrier_id or picking.carrier_id.delivery_type != "taroff":
            return False
        reason =None
        barcode = picking.carrier_tracking_ref
        if not barcode:
            raise UserError(_("No tracking barcode on this picking."))
        payload = {
            "barcode": str(barcode),
            "reason": reason or _("User request"),
        }
        try:
            res = self.env['delivery.adapter.taroff'].sudo()._api_post(picking.carrier_id, "/Ordercancel", payload)
        except Exception as e:
            picking.message_post(body=_("ُaroff Cancel: HTTP error: %s") % e)
            return False

        picking.message_post(body=_("Taarog: Shipment %s cancelled successfully.") % picking.carrier_tracking_ref)
        picking.sudo().write({
            'carrier_tracking_ref': False,
            'carrier_tracking_code': False
                              })
        return True

@register_carrier("taroff", model_name="delivery.adapter.taroff")
class DeliveryAdapterTaroff(models.AbstractModel):
    _name = "delivery.adapter.taroff"
    _description = "Taroff Carrier Adapter"

    def _api_url(self, carrier, suffix):
        base = (carrier.taroff_base_url or TAROFF_DEFAULT_BASE).rstrip("/")
        return f"{base}/{suffix.lstrip('/')}"

    def _api_post(self, carrier, path, payload):
        url = self._api_url(carrier, path)
        headers = {"Content-Type": "application/json"}
        # بیشتر سرویس‌های Taroff «key» را داخل body می‌خواهند نه Header
        if isinstance(payload, dict) and carrier.taroff_api_key:
            payload = {**payload, "key": carrier.taroff_api_key}

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        _logger.info("Taroff POST %s payload=%s", url, data)
        try:
            resp = requests.post(url, data=data, headers=headers, timeout=30)
        except Exception as e:
            raise UserError(_("Taroff request error: %s") % e)

        txt = resp.text or ""
        _logger.info("Taroff RESP %s: %s", url, txt)
        # Taroff اغلب 200 می‌دهد حتی خطا؛ پس بدنه را چک می‌کنیم
        try:
            body = resp.json()
        except Exception:
            body = {}
        # قرارداد PDF: فیلدهای error / error_code / msg
        if body and (body.get("error") or body.get("error_code")):
            raise UserError(_("Taroff API error: %s") % (body.get("msg") or body))
        return body or txt

    def _split_name(self, name):
        """نام را به name/lastname ساده تقسیم کن."""
        if not name:
            return ("", "")
        parts = str(name).strip().split()
        if len(parts) == 1:
            return (parts[0], "")
        return (" ".join(parts[:-1]), parts[-1])

    def _calc_totals(self, picking):
        qty = 0.0
        weight = 1
        # for ml in picking.move_line_ids:
        #     qty += (ml.qty_done or ml.product_uom_qty or 0.0)
        #     weight += (ml.product_id.weight or 0.0) * (ml.qty_done or ml.product_uom_qty or 0.0)
        # مقدار ریالی مرسوله (اختیاری): از مبلغ سفارش/فاکتور اگر داشتی
        parcelvalue = 0
        so = picking.sale_id
        if so:
            parcelvalue = int(round(so.amount_total * 10))  # تبدیل به ریال
        return max(int(qty), 1), int(round(weight)), int(parcelvalue)

    def _build_import_payload(self, carrier, picking):
        partner = picking.partner_id.commercial_partner_id
        name, last = self._split_name(partner.name or "")
        city = (partner.city or "").strip()
        phone = (partner.mobile or partner.phone or "").strip()
        cell = phone if carrier.taroff_use_mobile_as_phone else (partner.mobile or "")
        addr = ", ".join(filter(None, [partner._display_address().replace("\n", " ")]))
        content = ", ".join(
            sorted({ml.product_id.display_name for ml in picking.move_line_ids})
        ) or _("Goods")
        qty, weight, parcelvalue = self._calc_totals(picking)

        # زمان‌ها
        sched = picking.sale_id.select_deliver_date or  picking.scheduled_date or fields.Datetime.now()
        if isinstance(sched, datetime):
            local_dt = fields.Datetime.context_timestamp(self.env.user, sched)
        else:
            local_dt = sched
        if picking.delivery_slot=='morning':
            shift = 1
            req_dt = _to_jdate_str(local_dt)
        else:
            shift = 2
            req_dt = _to_jdate_str(local_dt)

        payload = {
            # کلید API در _api_post تزریق می‌شود
            "name": name or partner.name or "",
            "lastname": last,
            "city": city,
            "phone": phone.replace(" ",""),
            "cell": cell.replace(" ",""),
            "addr": addr,
            "content": content,
            "qty": qty,
            "weight": weight,
            "vol": int(carrier.taroff_default_vol or "0"),
            "packing": carrier.taroff_default_packing or "",
            "parcelvalue": parcelvalue,
            "orderID": picking.origin,  # شناسه سفارش/حواله
            "shift": shift,           # 1 یا 2
            "req_date": req_dt,       # جلالی yyyy/mm/dd
            "location": "",           # lat,long if you have
            "comment": "",
            "order_type": int(carrier.taroff_default_order_type or "1"),
            # import سرویس‌های پولی: اگر لازم شد از Getpricev2 قبلش بگیر و این‌ها رو هم ست کن
            # "price": ...,
            # "payment": 1/0,
            "cod": int(carrier.taroff_cod or "0"),
            # "shipment": 1/0,
        }
        # صحت حداقل‌ها
        if not payload["city"]:
            raise UserError(_("Taroff: Receiver city is required."))
        if not payload["phone"]:
            raise UserError(_("Taroff: Receiver phone/mobile is required."))
        return payload

    def send_for_picking(self, carrier, picking):
        """
        ارسال سفارش به Taroff و برگرداندن barcode برای ذخیره در carrier_tracking_ref
        از سرویس /Import استفاده می‌کنیم تا بلافاصله بارکد بدهد.
        """
        payload = self._build_import_payload(carrier, picking)
        result = self._api_post(carrier, "/Import", payload)
        if isinstance(result, dict) and result.get("barcode"):
            picking.sudo().write({
                "carrier_tracking_ref": result["barcode"],
                "carrier_tracking_code": result["barcode"],
                                  })

            return str(result["barcode"])
        # بعضی پیاده‌سازی‌ها آرایه/رشته برمی‌گردانند؛ هندل مقاوم:
        if isinstance(result, dict):
            # گاهی msg شامل بارکد است
            bc = result.get("barcode") or result.get("Barcode") or ""
            if bc:
                picking.sudo().write({
                    "carrier_tracking_ref": bc,
                    "carrier_tracking_code": bc
                                      })
                return str(bc)
        raise UserError(_("Taroff: no barcode returned. Response: %s") % result)

