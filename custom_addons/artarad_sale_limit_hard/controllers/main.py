# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo.addons.website_sale.controllers import main as website_sale_controller

from odoo.addons.website_sale.controllers.variant import WebsiteSaleVariantController
from odoo import http, fields, _
from odoo.exceptions import ValidationError
from odoo.http import request, route

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.payment.controllers import portal as payment_portal



class WebsiteSaleVariantControllerEx(WebsiteSaleVariantController):
    @route()
    def get_combination_info_website(self, *args, **kwargs):
        combination = super().get_combination_info_website(*args, **kwargs)
        # print("product._get_cart_qty(website)", combination)
        if combination.get("product_id"):
            # product = request.env['product.product'].sudo().browse(combination['product_id'])

            product_id = combination.get("product_id")
            product_id = request.env["product.product"].browse(product_id)
            website = request.env['website'].get_current_website()
            cart = website.sale_get_order() or None
            cart_qty = 0
            if cart:
                cart_qty = sum(
                    cart._get_common_product_lines(product=product_id).mapped('product_uom_qty')
                )
            res = product_id.get_variant_qty_limit(cart_qty, main_check=True,addqty=kwargs['add_qty'])
            # print("MAIN")
            combination.update(res)
        return combination


# class WebsiteSalesLimitQty(WebsiteSale):
#     @http.route(['/shop/confirmation'], type='http', auth="public", website=True, sitemap=False)
#     def shop_payment_confirmation(self, **post):
#         sale_order_id = request.session.get('sale_last_order_id')
#         if sale_order_id:
#             order_id = request.env['sale.order'].sudo().browse(sale_order_id)
#             update_ok = True
#             if order_id.partner_id.last_limit_line_update_order_id and order_id.partner_id.last_limit_line_update_order_id.id == order_id.id:
#                 update_ok = False
#             limit_qty_product_line_ids = order_id.order_line.filtered(lambda line: line.product_id.apply_qty_limit)
#             if limit_qty_product_line_ids and update_ok:
#                 if order_id.partner_id.product_limit_line_ids:
#                     product_limit_line_ids = order_id.partner_id.product_limit_line_ids.ids
#                     existing_product_limit_line_ids = request.env["partner.product.limit"].search(
#                         [("id", "in", product_limit_line_ids),
#                          ("product_id", "in", limit_qty_product_line_ids.mapped("product_id").ids)])
#
#                     limit_lines = []
#                     for limit_qty_product_line_id in limit_qty_product_line_ids:
#                         product_limit_line = existing_product_limit_line_ids.filtered(
#                             lambda line: line.product_id.id == limit_qty_product_line_id.product_id.id)
#                         if product_limit_line:
#                             product_limit_line.ordered_qty += limit_qty_product_line_id.product_uom_qty
#                         else:
#                             limit_lines.append((0, 0, {
#                                 "product_id": limit_qty_product_line_id.product_id.id,
#                                 "partner_id": order_id.partner_id.id,
#                                 "ordered_qty": limit_qty_product_line_id.product_uom_qty,
#                                 "limit_start_date": fields.Datetime().now().date(),
#                                 "limit_end_date": fields.Datetime().now().date() + timedelta(
#                                     days=limit_qty_product_line_id.product_id.remove_customer_limit_after)
#                             }))
#                     if limit_lines:
#                         order_id.partner_id.product_limit_line_ids = limit_lines
#                         order_id.partner_id.last_limit_line_update_order_id = order_id.id
#                 else:
#                     limit_lines = []
#                     for limit_qty_product_line_id in limit_qty_product_line_ids:
#                         limit_lines.append((0, 0, {
#                             "product_id": limit_qty_product_line_id.product_id.id,
#                             "partner_id": order_id.partner_id.id,
#                             "ordered_qty": limit_qty_product_line_id.product_uom_qty,
#                             "limit_start_date": fields.Datetime().now().date(),
#                             "limit_end_date": fields.Datetime().now().date() + timedelta(
#                                 days=limit_qty_product_line_id.product_id.remove_customer_limit_after)
#                         }))
#                     order_id.partner_id.product_limit_line_ids = limit_lines
#                     order_id.partner_id.last_limit_line_update_order_id = order_id.id
#
#         res = super(WebsiteSalesLimitQty, self).shop_payment_confirmation(**post)
#         return res


class PaymentPortal(payment_portal.PaymentPortal):

    @http.route()
    def shop_payment_transaction(self, order_id, access_token, **kwargs):
        order = request.website.sale_get_order()
        values = []
        for line in order.order_line:
            if line.product_id.type == 'consu':

                cart_qty = sum(order.order_line.filtered(lambda p: p.product_id.id == line.product_id.id).mapped(
                    'product_uom_qty'))
                res = line.product_id.get_variant_qty_limit(cart_qty)
                # print("res", res)
                apply_qty_limit = res.get("apply_qty_limit")
                limit_min = res.get("limit_min")
                limit_max = res.get("limit_max")
                limit_reached = res.get("limit_reached")
                # avl_qty = line.product_id.with_context(warehouse=order.warehouse_id.id).free_qty
                # if apply_qty_limit and limit_reached == "yes" and cart_qty > limit_max:
                #     values.append(_(
                #         'You ask for %(quantity)s products but only %(available_qty)s is available',
                #         quantity=cart_qty,
                #         available_qty=limit_max if limit_max > 0 else 0
                #     ))
                if apply_qty_limit and limit_reached == "crossed":
                    values.append(
                        _('You are willing to order more than the allowed quantity for %(product)s. Maximum allowed '
                          'quantity is %(max_qty)s, So reduce the quantity',
                          max_qty=limit_max if limit_max > 0 else 0,
                          product=line.product_id.name
                          ))
                    values.append(
                        _("OR You already purchased the allowed quantity of this product in previous orders , "
                          "So remove the product from the cart to process the payment"))
                if apply_qty_limit and cart_qty < limit_min:
                    values.append(
                        _('You are willing to order too less quantity for %(product)s. Minimum allowed quantity is %('
                          'limit_min)s, So add more quantity',
                          limit_min=limit_min if limit_min > 0 else 0,
                          product=line.product_id.name
                          ))
        if values:
            raise ValidationError('. '.join(values) + '.')
        return super().shop_payment_transaction(order_id, access_token,**kwargs)
