# -*- coding: utf-8 -*-
from odoo import models, fields
from datetime import timedelta

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_backorder_lead_days(self):
        self.ensure_one()
        company = self.company_id or self.order_id.company_id or self.env.company

        if self.qty_available_today >self.product_uom_qty :
            return self.customer_lead or 0.0
        else:
            return self.product_id.backorder_lead_days or company.sale_backorder_lead_days or 0.0

    def _expected_date(self):
        self.ensure_one()
        if self.state == 'sale' and self.order_id.date_order:
            order_date = self.order_id.date_order
        else:
            order_date = fields.Datetime.now()
        lead_days = self._get_backorder_lead_days()

        return order_date + timedelta(days=lead_days)