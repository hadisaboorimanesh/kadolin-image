# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.http import request


class ProductProduct(models.Model):
    _inherit = "product.product"

    apply_qty_limit = fields.Boolean()
    min_limit = fields.Integer()
    max_limit = fields.Integer()
    remove_customer_limit_after = fields.Integer()

    def get_variant_qty_limit(self, cart_qty=0, main_check=False,addqty=0):
        # print("---------- limit", cart_qty, self)
        apply_qty_limit = self.apply_qty_limit
        limit_status = "low"
        res = {}
        if request.website and request.website.enable_product_limits and apply_qty_limit:
            order = request.website.sale_get_order()
            if order:
                    # Show product's default limits
                    minimum_allowed_qty = self.min_limit
                    maximum_allowed_qty = self.max_limit
                    if not main_check:
                        if cart_qty > minimum_allowed_qty:
                            minimum_allowed_qty = 1
                    else:
                        if cart_qty >= minimum_allowed_qty:
                            minimum_allowed_qty = 1
                    remaining_maximum_allowed_qty = maximum_allowed_qty - cart_qty
                    if remaining_maximum_allowed_qty > 0:
                        limit_status = "low"
                    elif remaining_maximum_allowed_qty == 0:
                        limit_status = "equal"
                    else:
                        limit_status = "crossed"
                        remaining_maximum_allowed_qty = 0


            else:
                    # Show product's default limits
                    minimum_allowed_qty = self.min_limit
                    maximum_allowed_qty = self.max_limit
                    if not main_check:
                        if cart_qty > minimum_allowed_qty:
                            minimum_allowed_qty = 1
                    else:
                        if cart_qty >= minimum_allowed_qty:
                            minimum_allowed_qty = 1
                    remaining_maximum_allowed_qty = maximum_allowed_qty - cart_qty
                    if remaining_maximum_allowed_qty > 0:
                        limit_status = "low"
                    elif remaining_maximum_allowed_qty == 0:
                        limit_status = "equal"
                    else:
                        limit_status = "crossed"
                        remaining_maximum_allowed_qty = 0
            if remaining_maximum_allowed_qty == 0:
                minimum_allowed_qty = 0
                if main_check and limit_status == "equal":
                    limit_status = "crossed"
            res.update(
                {"limit_min": minimum_allowed_qty,
                 "limit_max": remaining_maximum_allowed_qty if main_check else maximum_allowed_qty,
                 "limit_reached": limit_status})
            res.update({"apply_qty_limit": apply_qty_limit})

        return res

