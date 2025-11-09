# -*- coding: utf-8 -*-
from odoo import fields, models

from odoo import fields, models

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    daily_capacity = fields.Integer(
        string='ظرفیت روزانه تحویل',
        help='حداکثر تعداد سفارشاتی که می‌توان در یک روز با این روش تحویل داد.',
        default=0
    )

class DeliveryCarrierLog(models.Model):
    _name = "delivery.carrier.log"
    _description = "Delivery Carrier Request Log"
    _order = "id desc"

    picking_id = fields.Many2one("stock.picking", ondelete="set null")
    carrier_id = fields.Many2one("delivery.carrier", ondelete="set null")
    status = fields.Selection([
        ("success", "Success"),
        ("error", "Error"),
        ("pending", "Pending"),
    ], default="pending")
    request_payload = fields.Text()
    response_text = fields.Text()
    error_text = fields.Text()