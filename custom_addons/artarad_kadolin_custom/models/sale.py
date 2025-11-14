# -*- coding: utf-8 -*-
from odoo import models, fields,api
from datetime import timedelta

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    org_route_id = fields.Many2one(
        'stock.route',
        string="Route for Organization Sale Orders",
    )
    select_deliver_date = fields.Date(tracking=True)
    delivery_slot = fields.Selection([
        ('morning', '9 تا 15'),
        ('evening', '15 تا 21'),
    ], string="Delivery Slot", tracking=True,help="زمان‌بندی تحویل برای مشتری در شهر تهران",index=True,)

    @api.depends('order_line.customer_lead', 'date_order', 'state')
    def _compute_expected_date(self):
        """ For service and consumable, we only take the min dates. This method is extended in sale_stock to
            take the picking_policy of SO into account.
        """
        self.mapped("order_line")  # Prefetch indication
        for order in self:
            if order.state == 'cancel':
                order.expected_date = False
                continue
            dates_list = order.order_line.filtered(
                lambda line: not line.display_type and not line._is_delivery()
            ).mapped(lambda line: line and line._expected_date())
            if dates_list:
                order.expected_date = order._select_expected_date(dates_list)
            else:
                order.expected_date = False
            if order.select_deliver_date:
                order.expected_date = order.select_deliver_date

    def action_confirm(self):
        ICP = self.env['ir.config_parameter'].sudo()
        route_id_str = ICP.get_param('sale.single_line_route_id')
        for order in self:
            if route_id_str and not order.org_route_id:
                route = self.env['stock.route'].browse(int(route_id_str))
                # فقط لاین‌های کالایی (stockable) با مقدار مثبت
                stock_lines = order.order_line.filtered(
                    lambda l: l.product_id and l.product_id.type != 'service' and l.product_uom_qty==1
                )
                sale_lines = order.order_line.filtered(
                    lambda l: l.product_id and l.product_id.type != 'service'
                )
                if len(stock_lines) == 1 and len(sale_lines)==1 and  route :
                    line = stock_lines[0]
                    line.route_id = route
            if order.org_route_id:
                order.order_line.route_id = order.org_route_id.id

        return super().action_confirm()


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