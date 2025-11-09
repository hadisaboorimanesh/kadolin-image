# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.http import request


class ProductProduct(models.Model):
    _inherit = "product.product"

    apply_qty_limit = fields.Boolean()
    min_limit = fields.Integer()
    max_limit = fields.Integer()
    remove_customer_limit_after = fields.Integer()

    def get_variant_qty_limit(self, cart_qty=0, main_check=False):
        # print("---------- limit", cart_qty, self)
        apply_qty_limit = self.apply_qty_limit
        limit_status = "low"
        res = {}
        if request.website and request.website.enable_product_limits and apply_qty_limit:
            order = request.website.sale_get_order()
            if order:
                # IF PUBLIC ORDER
                # print("----------------", order.partner_id.id, request.website.user_id.partner_id.id)
                if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
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
                        # minimum_allowed_qty = 0

                    # if cart_qty == maximum_allowed_qty and limit_status != "crossed":
                    #     # maximum_allowed_qty = 0
                    #     limit_status = "crossed"
                    #     minimum_allowed_qty = 0

                # IF ORDER LINKED TO A PARTNER
                else:
                    # Check product limit lines in partner
                    today = fields.Date.today()
                    limit_line_ids = request.env["partner.product.limit"].search(
                        [("partner_id", "=", order.partner_id.id), ("product_id", "=", self.id),
                         ("limit_start_date", "<=", today), ("limit_end_date", ">=", today)])
                    if limit_line_ids:
                        # Already purchased some limited items
                        already_ordered_qty = limit_line_ids[0].ordered_qty
                        minimum_allowed_qty = 1
                        maximum_allowed_qty = self.max_limit - already_ordered_qty

                        # total_ordered_qty = already_ordered_qty + cart_qty
                        remaining_maximum_allowed_qty = maximum_allowed_qty - cart_qty

                        if remaining_maximum_allowed_qty > 0:
                            limit_status = "low"
                        elif remaining_maximum_allowed_qty == 0:
                            limit_status = "equal"
                        else:
                            limit_status = "crossed"
                            remaining_maximum_allowed_qty = 0
                            # minimum_allowed_qty = 0

                        # if already_ordered_qty == self.max_limit:
                        #     limit_status = "crossed"
                        #     remaining_maximum_allowed_qty = 0
                        #     minimum_allowed_qty = 0

                    else:
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
                            # minimum_allowed_qty = 0

                        # if cart_qty == self.max_limit:
                        #     limit_status = "crossed"
                        #     remaining_maximum_allowed_qty = 0
                        #     # minimum_allowed_qty = 0
                        # print("remaining_maximum_allowed_qty", remaining_maximum_allowed_qty)
            else:
                # print("NO order")
                if request.website.is_public_user():
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
                    # Existing logged in User
                    today = fields.Date.today()
                    # print("EXisting User", today, self.env.user.partner_id)
                    limit_line_ids = request.env["partner.product.limit"].search(
                        [("partner_id", "=", self.env.user.partner_id.id), ("product_id", "=", self.id),
                         ("limit_start_date", "<=", today), ("limit_end_date", ">=", today)])
                    # print("limit_line_ids", limit_line_ids)
                    if limit_line_ids:
                        # Already purchased some limited items
                        already_ordered_qty = limit_line_ids[0].ordered_qty
                        minimum_allowed_qty = 1
                        maximum_allowed_qty = self.max_limit - already_ordered_qty

                        # total_ordered_qty = already_ordered_qty + cart_qty
                        remaining_maximum_allowed_qty = maximum_allowed_qty - cart_qty

                        if remaining_maximum_allowed_qty > 0:
                            limit_status = "low"
                        elif remaining_maximum_allowed_qty == 0:
                            limit_status = "equal"
                        else:
                            limit_status = "crossed"
                            remaining_maximum_allowed_qty = 0
                            # minimum_allowed_qty = 0

                        # if already_ordered_qty == self.max_limit:
                        #     limit_status = "crossed"
                        #     remaining_maximum_allowed_qty = 0
                        #     minimum_allowed_qty = 0

                    else:
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
                            # minimum_allowed_qty = 0

            if remaining_maximum_allowed_qty == 0:
                minimum_allowed_qty = 0
                if main_check and limit_status == "equal":
                    limit_status = "crossed"
            res.update(
                {"limit_min": minimum_allowed_qty,
                 "limit_max": remaining_maximum_allowed_qty if main_check else maximum_allowed_qty,
                 "limit_reached": limit_status})
            res.update({"apply_qty_limit": apply_qty_limit})

        # print("response ----------> ", res)
        return res


class ResPartner(models.Model):
    _inherit = "res.partner"

    last_limit_line_update_order_id = fields.Many2one("sale.order")
    product_limit_line_ids = fields.One2many("partner.product.limit", "partner_id")


class PartnerProductLimit(models.Model):
    _name = "partner.product.limit"

    product_id = fields.Many2one("product.product")
    partner_id = fields.Many2one("res.partner")
    ordered_qty = fields.Integer()
    limit_start_date = fields.Date()
    limit_end_date = fields.Date()

    # is_limit_active = fields.Boolean()

    @api.model
    def _run_restriction_cleaner(self):
        today = fields.Date.today()
        ids = self.sudo().search([("limit_end_date", "<=", today)])
        if ids:
            ids.unlink()


class Website(models.Model):
    _inherit = "website"

    enable_product_limits = fields.Boolean()
