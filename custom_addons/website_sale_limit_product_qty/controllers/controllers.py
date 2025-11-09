# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo.addons.website_sale.controllers.variant import WebsiteSaleVariantController
from odoo import http, fields, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.payment import utils as payment_utils
from datetime import datetime
from odoo.http import request, route
from odoo.http import Controller, request, route


# controllers/configurator_limit.py
# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from odoo.http import request, route
# مهم: از کنترلر website_sale ارث‌بری کن، نه sale
from odoo.addons.sale.controllers.product_configurator import SaleProductConfiguratorController

_logger = logging.getLogger(__name__)


from odoo.http import request, route
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo import _

class WebsiteSaleQtyLimiter(WebsiteSale):

    def _get_limit_info(self, product, current_qty=0):
        """برگشت اطلاعات سقف خرید برای variant. تابع get_variant_qty_limit اگه داری از همونه استفاده کن،
        وگرنه از فیلدهای apply_qty_limit / max_limit استفاده می‌کنیم."""
        limit_max = 0
        if hasattr(product, 'get_variant_qty_limit'):
            info = product.get_variant_qty_limit(current_qty) or {}
            limit_max = int(info.get('limit_max') or 0)
            apply = bool(info.get('apply', getattr(product, 'apply_qty_limit', False)))
        else:
            apply = bool(getattr(product, 'apply_qty_limit', False))
            limit_max = int(getattr(product, 'max_limit', 0) or 0)
        return apply, limit_max

    def _apply_qty_ceiling(self, order_sudo, line_id, product_id):
        """اگر مقدار خط از سقف بالاتر بود، به سقف برگردان."""
        if not line_id:
            return None
        line = request.env['sale.order.line'].sudo().browse(line_id)
        if not line or not line.exists():
            return None
        product = request.env['product.product'].sudo().browse(product_id)
        if not product or not product.exists():
            return None

        apply, limit_max = self._get_limit_info(product, current_qty=line.product_uom_qty or 0)
        if apply and limit_max and line.product_uom_qty > limit_max:
            # اصلاح به سقف
            order_sudo._cart_update(
                product_id=product.id,
                line_id=line.id,
                set_qty=limit_max,
            )
            return {
                'clamped': True,
                'line_id': line.id,
                'limit_max': limit_max,
                'new_qty': limit_max,
            }
        return {
            'clamped': False,
            'line_id': line.id,
            'limit_max': limit_max,
            'new_qty': line.product_uom_qty,
        }

    @route(
        route='/website_sale/product_configurator/update_cart',
        type='json',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def website_sale_product_configurator_update_cart(
        self, main_product, optional_products, **kwargs
    ):
        """Override: بعد از هر _cart_update سقف را enforce می‌کنیم."""
        order_sudo = request.website.sale_get_order(force_create=True)
        if order_sudo.state != 'draft':
            request.session['sale_order_id'] = None
            order_sudo = request.website.sale_get_order(force_create=True)

        # Main product
        values = order_sudo._cart_update(
            product_id=main_product['product_id'],
            add_qty=main_product['quantity'],
            product_custom_attribute_values=main_product['product_custom_attribute_values'],
            no_variant_attribute_value_ids=[int(v) for v in main_product['no_variant_attribute_value_ids']],
            **kwargs,
        )
        line_ids = {main_product['product_template_id']: values['line_id']}

        # Enforce ceiling for main line
        main_clamp = self._apply_qty_ceiling(order_sudo, values['line_id'], main_product['product_id'])

        # Optionals
        if optional_products and values['line_id']:
            for option in optional_products:
                option_values = order_sudo._cart_update(
                    product_id=option['product_id'],
                    add_qty=option['quantity'],
                    product_custom_attribute_values=option['product_custom_attribute_values'],
                    no_variant_attribute_value_ids=[int(v) for v in option['no_variant_attribute_value_ids']],
                    linked_line_id=line_ids[option['parent_product_template_id']],  # عمداً index می‌زنیم تا داده غلط فاش شود
                    **kwargs,
                )
                line_ids[option['product_template_id']] = option_values['line_id']
                # Enforce ceiling for each optional
                self._apply_qty_ceiling(order_sudo, option_values['line_id'], option['product_id'])

        # Build response
        values['notification_info'] = self._get_cart_notification_information(order_sudo, line_ids.values())
        # اگر main clamp شد، یک هشدار هم بدهیم (اختیاری)
        if main_clamp and main_clamp.get('clamped'):
            warn = _("تعداد درخواست‌شده بیش از سقف مجاز بود و به %(max)s تنظیم شد.", max=main_clamp['limit_max'])
            values['notification_info']['warning'] = warn

        values['cart_quantity'] = order_sudo.cart_quantity
        request.session['website_sale_cart_quantity'] = order_sudo.cart_quantity
        return values

class ProductConfiguratorController(SaleProductConfiguratorController,WebsiteSale):

    @route(
        route='/website_sale/product_configurator/update_combination',
        type='json', auth='public', methods=['POST'], website=True
    )
    def website_sale_product_configurator_update_combination(self, *args, **kwargs):
        # همانی که اودو انجام می‌دهد (پریس‌لیست/ارز را در kwargs می‌گذارد)
        self._populate_currency_and_pricelist(kwargs)

        # استخراج ورودی‌ها
        pt_id = int(kwargs.get('product_template_id') or 0)
        ptav_ids = [int(x) for x in (kwargs.get('ptav_ids') or [])]
        requested_qty = float(kwargs.get('quantity') or 0.0)

        # پیدا کردن واریانت نهایی
        product_template = request.env['product.template'].browse(pt_id)
        combination = request.env['product.template.attribute.value'].browse(ptav_ids)
        product = product_template._get_variant_for_combination(combination) or product_template

        # clamp کردن مقدار بر اساس منطق limit خودت
        clamped_qty = requested_qty
        limit_info = {}
        if getattr(product, 'apply_qty_limit', False):
            limit_info = (product.sudo().get_variant_qty_limit(requested_qty) or {})
            limit_min = int(limit_info.get('limit_min') or 0)
            limit_max = int(limit_info.get('limit_max') or 0)
            if limit_max and clamped_qty > limit_max:
                clamped_qty = float(limit_max)
            if limit_min and clamped_qty < limit_min:
                clamped_qty = float(limit_min)

        # جایگزینی quantity قبل از صدا زدن متد اصلی sale
        kwargs['quantity'] = clamped_qty

        # فراخوانی منطق اصلی (همان متدی که اودو در نهایت صدا می‌زند)
        values = super().sale_product_configurator_update_combination(*args, **kwargs)

        # اطلاعات کمکی برای UI (اختیاری)
        values.setdefault('requested_quantity', requested_qty)
        values.setdefault('quantity', clamped_qty)
        values.setdefault('qty_limit', {
            'limit_min': limit_info.get('limit_min'),
            'limit_max': limit_info.get('limit_max'),
            'limit_reached': limit_info.get('limit_reached'),
        })
        if requested_qty > limit_max:
            raise UserError("sfdsafsdaf")

        return values

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
            res = product_id.get_variant_qty_limit(cart_qty, main_check=True)
            print("res", res)
            # print("MAIN")
            combination.update(res)
        return combination


class WebsiteSalesLimitQty(WebsiteSale):
    @http.route(['/shop/confirmation'], type='http', auth="public", website=True, sitemap=False)
    def shop_payment_confirmation(self, **post):
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order_id = request.env['sale.order'].sudo().browse(sale_order_id)
            update_ok = True
            if order_id.partner_id.last_limit_line_update_order_id and order_id.partner_id.last_limit_line_update_order_id.id == order_id.id:
                update_ok = False
            limit_qty_product_line_ids = order_id.order_line.filtered(lambda line: line.product_id.apply_qty_limit)
            if limit_qty_product_line_ids and update_ok:
                if order_id.partner_id.product_limit_line_ids:
                    product_limit_line_ids = order_id.partner_id.product_limit_line_ids.ids
                    existing_product_limit_line_ids = request.env["partner.product.limit"].search(
                        [("id", "in", product_limit_line_ids),
                         ("product_id", "in", limit_qty_product_line_ids.mapped("product_id").ids)])

                    limit_lines = []
                    for limit_qty_product_line_id in limit_qty_product_line_ids:
                        product_limit_line = existing_product_limit_line_ids.filtered(
                            lambda line: line.product_id.id == limit_qty_product_line_id.product_id.id)
                        if product_limit_line:
                            product_limit_line.ordered_qty += limit_qty_product_line_id.product_uom_qty
                        else:
                            limit_lines.append((0, 0, {
                                "product_id": limit_qty_product_line_id.product_id.id,
                                "partner_id": order_id.partner_id.id,
                                "ordered_qty": limit_qty_product_line_id.product_uom_qty,
                                "limit_start_date": fields.Datetime().now().date(),
                                "limit_end_date": fields.Datetime().now().date() + timedelta(
                                    days=limit_qty_product_line_id.product_id.remove_customer_limit_after)
                            }))
                    if limit_lines:
                        order_id.partner_id.product_limit_line_ids = limit_lines
                        order_id.partner_id.last_limit_line_update_order_id = order_id.id
                else:
                    limit_lines = []
                    for limit_qty_product_line_id in limit_qty_product_line_ids:
                        limit_lines.append((0, 0, {
                            "product_id": limit_qty_product_line_id.product_id.id,
                            "partner_id": order_id.partner_id.id,
                            "ordered_qty": limit_qty_product_line_id.product_uom_qty,
                            "limit_start_date": fields.Datetime().now().date(),
                            "limit_end_date": fields.Datetime().now().date() + timedelta(
                                days=limit_qty_product_line_id.product_id.remove_customer_limit_after)
                        }))
                    order_id.partner_id.product_limit_line_ids = limit_lines
                    order_id.partner_id.last_limit_line_update_order_id = order_id.id

        res = super(WebsiteSalesLimitQty, self).shop_payment_confirmation(**post)
        return res


    @http.route(['/shop/cart/update_json'], type='json', auth="public", methods=['POST'], website=True)
    def cart_update_json(
            self, product_id, line_id=None, add_qty=None, set_qty=None, display=True,
            product_custom_attribute_values=None, no_variant_attribute_value_ids=None, **kwargs
    ):
        # 1) بگذار منطق استاندارد اجرا شود
        values = super().cart_update_json(
            product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty, display=False,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_value_ids=no_variant_attribute_value_ids, **kwargs
        )

        # اگر سفارشی نشد (به خاطر state و ...) همان را برگردان
        if not values or not values.get('line_id'):
            # super با display=False برگشته؛ اگر display=True خواسته شده، الان رندر می‌کنیم
            if display and request.website.sale_get_order():
                order = request.website.sale_get_order()
                values['cart_ready'] = order._is_cart_ready()
                values['website_sale.cart_lines'] = request.env['ir.ui.view']._render_template(
                    "website_sale.cart_lines", {
                        'website_sale_order': order,
                        'date': fields.Date.today(),
                        'suggested_products': order._cart_accessories()
                    }
                )
                values['website_sale.total'] = request.env['ir.ui.view']._render_template(
                    "website_sale.total", {'website_sale_order': order}
                )
            return values

        # 2) کنترل سقف
        line = request.env['sale.order.line'].browse(values['line_id'])
        order = line.order_id
        product = line.product_id

        # اگر متد سفارشی داری (برای هر واریانت)، از آن استفاده کن؛ وگرنه از فیلدها
        limit_max = 0
        apply_limit = False
        if hasattr(product, 'get_variant_qty_limit'):
            info = product.get_variant_qty_limit(line.product_uom_qty) or {}
            limit_max = int(info.get('limit_max') or 0)
            apply_limit = bool(getattr(product, 'apply_qty_limit', False) or info.get('apply_qty_limit'))
        else:
            limit_max = int(getattr(product, 'max_limit', 0) or 0)
            apply_limit = bool(getattr(product, 'apply_qty_limit', False))

        if apply_limit and limit_max > 0 and line.product_uom_qty > limit_max:
            # مقدار را به سقف برگردان
            order.sudo()._cart_update(
                product_id=product.id,
                line_id=line.id,
                set_qty=limit_max,
                **kwargs
            )
            # به‌روز کردن اعداد و پیغام هشدار
            values['quantity'] = limit_max
            values['notification_info'] = self._get_cart_notification_information(order, [line.id])
            # values['notification_info']['warning'] = http._("Maximum quantity for this product is %s.", limit_max)

        # 3) اعداد سبد و رندر قالب‌ها
        request.session['website_sale_cart_quantity'] = order.cart_quantity
        if not order.cart_quantity:
            request.website.sale_reset()
            return values

        values['cart_quantity'] = order.cart_quantity
        values['minor_amount'] = payment_utils.to_minor_currency_units(order.amount_total, order.currency_id)
        values['amount'] = order.amount_total

        if display:
            values['cart_ready'] = order._is_cart_ready()
            values['website_sale.cart_lines'] = request.env['ir.ui.view'].sudo()._render_template(
                "website_sale.cart_lines", {
                    'website_sale_order': order.sudo(),
                    'date': fields.Date.today(),
                    'suggested_products': order.sudo()._cart_accessories()
                }
            )
            values['website_sale.total'] = request.env['ir.ui.view'].sudo()._render_template(
                "website_sale.total", {'website_sale_order': order.sudo()}
            )

        return values


class PaymentPortal(payment_portal.PaymentPortal):

    @http.route()
    def shop_payment_transaction(self, order_id, access_token, **kwargs):
        order = request.website.sale_get_order()
        values = []
        for line in order.order_line:
            if line.product_id.type == 'product':

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
