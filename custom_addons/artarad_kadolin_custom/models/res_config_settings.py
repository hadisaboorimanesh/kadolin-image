# -*- coding: utf-8 -*-
from odoo import models, fields

class ResCompany(models.Model):
    _inherit = "res.company"

    sale_backorder_lead_days = fields.Float(
        string="Backorder Lead Time (days)",
        help="Fallback lead time if the product is not in stock and the product has no specific backorder lead time.",
        default=0.0,
    )
    #
    # single_line_route_id = fields.Many2one(
    #         'stock.route',
    #         string="Route for Single-Line Sale Orders",
    #         help="If a sale order has only one line, this route will be applied automatically."
    #     )

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sale_backorder_lead_days = fields.Float(
        related="company_id.sale_backorder_lead_days",
        readonly=False,
        string="Backorder Lead Time (days)",
        help="Default lead time when product is not in stock (used if product has no specific value).",
    )

    # single_line_route_id = fields.Many2one(
    #     'stock.route',
    #     string="Route for Single-Line Sale Orders",
    #     config_parameter='company_id.single_line_route_id',
    #     help="If a sale order has only one line, this route will be applied automatically."
    # )
    single_line_route_id = fields.Many2one(
        'stock.route',
        string="Route for Single-Line Sale Orders",
        config_parameter='sale.single_line_route_id',
        help="If a sale order has only one line, this route will be applied automatically."
    )