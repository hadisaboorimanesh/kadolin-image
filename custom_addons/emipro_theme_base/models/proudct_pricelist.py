# -*- coding: utf-8 -*-

from odoo import fields, models, api


class PriceList(models.Model):
    _inherit = "product.pricelist"

    enable_price_table = fields.Boolean('Price Table?',
                                        help='Display Price table for more than one minimum quantity rule')
