import logging
from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)




class SaleOrder(models.Model):
    _inherit = "sale.order"

    settle_status = fields.Char(readonly=True,copy=False)

    def snapp_inquery(self):
        for t in self.transaction_ids.filtered(lambda l:l.state=='done' and l.provider_id.code=='snappay'):
            try:
                res = t.provider_id.snappay_status(t.snappay_payment_token)
                if not (res or {}).get('successful'):
                        self.settle_status = res
                else:
                        self.settle_status = res

            except Exception:
                self.settle_status = res

    def update_snapp(self):
        for t in self.transaction_ids.filtered(lambda l:l.state=='done' and l.provider_id.code=='snappay'):
            t.snappay_update_payment()
            self.message_post(body=_("سفارش با موفقیت در اسنپ پی بروزرسانی شد.") )
    def cancel_snapp(self):
        for t in self.transaction_ids.filtered(lambda l:l.state=='done' and l.provider_id.code=='snappay'):
            t.snappay_cancel_payment()
            self.message_post(body=_("سفارش با موفقیت در اسنپ پی لغو گردید.") )

