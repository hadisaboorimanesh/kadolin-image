# -*- coding: utf-8 -*-

from odoo import api, models, _,fields
from odoo.exceptions import UserError
from .delivery_base import CARRIER_REGISTRY

class StockPicking(models.Model):
    _inherit = "stock.picking"

    carrier_tracking_code = fields.Char()

    def button_validate(self):
        res = super().button_validate()
        # فقط حواله خروجی، کریر ست شده، و هنوز بارنامه/ترکینگ نداریم
        for p in self:
            c = p.carrier_id
            if (
                    (p._is_pack())
                    and c
                    and c.delivery_type in CARRIER_REGISTRY
                    and not p.carrier_tracking_ref
            ):
                adapter_model = CARRIER_REGISTRY[c.delivery_type]
                adapter = self.env[adapter_model].sudo()
                try:
                    # آداپتر خودش ارسال را انجام می‌دهد، بارنامه را در carrier_tracking_ref می‌نویسد
                    # و پیام‌های لاگ را روی حواله ثبت می‌کند.
                    adapter.send_for_picking(c, p)
                except Exception as e:
                    # اینجا بلاک نکن (چون حواله همین الان validate شده)
                    # فقط لاگ کن و پیام بده
                    self.env["delivery.carrier.log"].sudo().create({
                        "picking_id": p.id,
                        "carrier_id": c.id,
                        "status": "error",
                        "error_text": str(e),
                    })
                    p.message_post(body=_("Carrier request failed: %s") % e)
                    # raise نکنیم تا وضعیت حواله خراب نشه
        return res

    def submit_delivery(self):
        for p in self:
            c = p.carrier_id
            if (
                    (p._is_pack())
                    and c
                    and c.delivery_type in CARRIER_REGISTRY
                    and not p.carrier_tracking_ref
            ):
                adapter_model = CARRIER_REGISTRY[c.delivery_type]
                adapter = self.env[adapter_model].sudo()
                try:
                    # آداپتر خودش ارسال را انجام می‌دهد، بارنامه را در carrier_tracking_ref می‌نویسد
                    # و پیام‌های لاگ را روی حواله ثبت می‌کند.
                    adapter.send_for_picking(c, p)
                except Exception as e:
                    # اینجا بلاک نکن (چون حواله همین الان validate شده)
                    # فقط لاگ کن و پیام بده
                    self.env["delivery.carrier.log"].sudo().create({
                        "picking_id": p.id,
                        "carrier_id": c.id,
                        "status": "error",
                        "error_text": str(e),
                    })
                    p.message_post(body=_("Carrier request failed: %s") % e)
                    # raise نکنیم تا وضعیت حواله خراب نشه
