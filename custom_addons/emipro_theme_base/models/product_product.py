# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    product_brand_id = fields.Many2one('product.brand', related='product_tmpl_id.product_brand_id')

    def remove_cart_button(self):
        return self.sudo().out_of_stock()

    def out_of_stock(self):
        if self.type == 'consu' and self.is_storable == True and not self.allow_out_of_stock_order and self.sudo().with_context(warehouse=request.website.warehouse_id.id).free_qty < 1:
            return True
        return False
