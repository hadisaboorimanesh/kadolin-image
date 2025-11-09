# controllers/stock_barcode.py
from odoo import  _
from odoo.http import  route
from odoo.addons.stock_barcode.controllers.stock_barcode import StockBarcodeController as CoreBarcodeController
from odoo.tools.safe_eval import safe_eval
import logging
import json
from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)
from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.website_sale.controllers.delivery import Delivery
from odoo import http, fields
from odoo.http import request, Response
from odoo.tools import html2plaintext
def _attr_summary_from_template(p_tmpl):
    parts = []
    # ترتیب بر اساس sequence خود خط و sequence ویژگی
    lines = p_tmpl.attribute_line_ids.sorted(
        key=lambda l: (l.sequence, l.attribute_id.sequence, l.attribute_id.name or "")
    )
    for line in lines:
        attr_name = (line.attribute_id and line.attribute_id.name) or ""
        # در v16+ مقادیر معمولاً از product_template_value_ids گرفته می‌شوند
        values = line.product_template_value_ids.mapped("product_attribute_value_id.name")
        if not values and hasattr(line, "value_ids"):
            # سازگاری
            values = line.value_ids.mapped("name")
        val_txt = "، ".join(v for v in values if v)
        if attr_name and val_txt:
            parts.append(f"{attr_name} : {val_txt}")
    return " | ".join(parts)

class WebsiteSaleDeliveryCapacity(Delivery):

    @http.route('/shop/set_delivery_method', type='json', auth='public', website=True, csrf=False)
    def shop_set_delivery_method(self, delivery_method_id=None, **kw):
        # 1) رفتار پیش‌فرض اودو
        base_resp = super().shop_set_delivery_method(delivery_method_id=delivery_method_id, **kw)

        # 2) ضمیمه‌کردن ظرفیت/روزها برای رندرِ فوری سمت JS
        try:
            order = request.website.sale_get_order()
            carrier = None
            if delivery_method_id:
                carrier = request.env['delivery.carrier'].sudo().browse(int(delivery_method_id))
            if not (carrier and carrier.exists()) and order:
                carrier = order.sudo().carrier_id

            if order and carrier and carrier.exists():
                availability = carrier.sudo()._slot_availability(
                    order=order,
                    start_date=(order.expected_date or fields.Date.today()),
                    horizon_days=30,
                    needed_free_days=5,
                )
                if not isinstance(base_resp, dict):
                    base_resp = {'status': 'ok'}
                base_resp.setdefault('kadolin', {})['slot_availability'] = availability
        except Exception:
            # اجازه نده خطای ما جریان اصلی را خراب کند
            pass

        return base_resp
class CityLookup(http.Controller):

    @http.route('/shop/delivery_slot/availability', type='json', auth='public', website=True, csrf=False)
    def delivery_slot_availability(self, dates=None, **kw):
        dates = dates or []
        res = {}
        if not dates:
            return res

        # Determine current order and selected carrier (delivery method)
        order = request.website.sale_get_order()
        carrier = None
        if order:
            # prefer the standard field name; fall back if customized
            carrier = getattr(order, 'carrier_id', None) or getattr(order, 'delivery_carrier_id', None)

        # Read daily capacity from carrier field if it exists; otherwise from ICP; otherwise fallback
        icp = request.env['ir.config_parameter'].sudo()
        default_cap = int(icp.get_param('delivery.capacity.default', default='50') or 50)
        daily_capacity = None
        if carrier is not None:
            # custom field expected to be defined on delivery.carrier (e.g., x_daily_capacity)
            daily_capacity = getattr(carrier, 'x_daily_capacity', None)
            try:
                # allow Char fields holding digits
                daily_capacity = int(daily_capacity) if daily_capacity not in (None, False, '') else None
            except Exception:
                daily_capacity = None
        if daily_capacity is None:
            daily_capacity = default_cap

        # Define slots (static for now). If you later store them on carrier, read from there.
        slots = ['09-12', '12-16', '16-20']
        per_slot_capacity = max(1, daily_capacity // len(slots)) if slots else daily_capacity

        # Build result day-by-day
        SO = request.env['sale.order'].sudo()
        for d in dates:
            # Count already booked for the day (only confirmed orders). If carrier exists, filter by it.
            domain_day = [('state', 'in', ['sale']), ('x_delivery_date', '=', d)]
            if carrier:
                domain_day.append(('carrier_id', '=', carrier.id))
            booked = SO.search_count(domain_day)

            slots_info = {}
            all_full = True if slots else False
            for slot in slots:
                domain_slot = list(domain_day) + [('x_delivery_slot', '=', slot)]
                booked_s = SO.search_count(domain_slot)
                full_s = booked_s >= per_slot_capacity if per_slot_capacity is not None else False
                slots_info[slot] = {
                    'capacity': per_slot_capacity,
                    'booked': booked_s,
                    'full': full_s,
                }
                if not full_s:
                    all_full = False

            day_full = all_full if slots else (booked >= daily_capacity if daily_capacity else False)
            res[d] = {
                'capacity': daily_capacity,
                'booked': booked,
                'full': day_full,
                'slots': slots_info,
            }
        return res

    @http.route('/torobapi/published_products', type='json', auth='public', methods=['POST', 'GET'])
    def get_torob_published_products(self):
        base = request.httprequest.host_url.rstrip('/')
        products = request.env['product.template'].sudo().search([('website_published', '=', True)])
        data = []
        for p in products:
            rel = getattr(p, 'website_url', False)
            product_url = base + rel if rel else base + f"/shop/product/{p.id}"
            image_url = f"{base}/web/image/product.template/{p.id}/image_512"
            data.append({
                'product_id': p.default_code,
                'title': p.name,
                'availability': 'instock' if (p.qty_available>0 or p.allow_out_of_stock_order ) else 'out_of_stock',
                'page_url': product_url,
                # 'image_link': image_url,
                'price': p.list_price,
                'old_price': p.compare_list_price,
            })
        return data

    # @http.route('/snappayapi/published_products', type='json', auth='public', methods=['POST','GET'])
    # def get_snapppay_published_products(self):
    #     base = request.httprequest.host_url.rstrip('/')
    #     products = request.env['product.template'].sudo().search([('website_published', '=', True)])
    #     data = []
    #     for p in products:
    #         rel = getattr(p, 'website_url', False)
    #         product_url = base + rel if rel else base + f"/shop/product/{p.id}"
    #         image_url = f"{base}/web/image/product.template/{p.id}/image_512"
    #         data.append({
    #             'title': p.name,
    #             'is_available': p.qty_available>0 or p.allow_out_of_stock_order ,
    #             'url': product_url,
    #             'image_link': image_url,
    #             'price': p.list_price,
    #             'old_price': p.compare_list_price,
    #          })
    #     return data
    @http.route('/snappayapi/published_products', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def get_snapppay_published_products(self, **kwargs):
        base = request.httprequest.host_url.rstrip('/')

        products = request.env['product.template'].sudo().search([
            ('website_published', '=', True)
        ])

        items = []
        for p in products:
            rel = (p.website_url or f"/shop/product/{p.id}")
            product_url = f"{base}{rel}"
            image_url = f"{base}/web/image/product.template/{p.id}/image_512"

            attrs_txt = _attr_summary_from_template(p)

            short_desc_txt = f" {attrs_txt} " if attrs_txt else ""

            # قیمت‌ها را به عدد صحیح تبدیل می‌کنیم تا مثل نمونه بدون اعشار باشند
            price = int(round(p.list_price or 0))
            old_price = int(round(getattr(p, 'compare_list_price', 0) or 0))

            items.append({
                "title": p.name or "",
                "price": price,
                "old_price": old_price,
                "url": product_url,
                "image_link": image_url,
                "short_description": short_desc_txt,
                "is_available": bool(
                    (getattr(p, 'qty_available', 0) or 0) > 0 or getattr(p, 'allow_out_of_stock_order', False)),
            })

        payload = {"products": items}
        body = json.dumps(payload, ensure_ascii=True)  # ← خروجی دقیقاً با \u… مثل نمونه
        return Response(
            body,
            content_type='application/json; charset=utf-8',
            status=200
        )
    @http.route('/shop/cities', type='http', auth='public', website=True, methods=['GET'])
    def shop_cities(self, state_id=None, **kw):
        try:
            sid = int(state_id or 0)
        except Exception:
            sid = 0
        City = request.env['res.city'].sudo()
        cities = City.search([('state_id', '=', sid)], order='name asc') if sid else City.browse([])
        payload = json.dumps([{'id': c.id, 'name': c.name} for c in cities])
        return request.make_response(payload, headers=[('Content-Type', 'application/json')])




    @http.route('/shop/delivery_availability', type='json', auth='public', website=True, csrf=False)
    def get_delivery_availability(self, days=10):
        """برمی‌گرداند [{date: '2025-10-29', remaining: 4, full: false}, ...]"""
        order = request.website.sale_get_order()
        if not order or not order.carrier_id:
            return []

        carrier = order.carrier_id.sudo()
        capacity = carrier.daily_capacity or 0
        delivery_product = carrier.product_id

        results = []
        today = order.expected_date or datetime.now().date()

        for i in range(days):
            target = today + timedelta(days=i)

            # دامنه‌ی سفارش‌های تأییدشده با همین محصول تحویل
            domain = [
                ('state', 'in', ('sale', 'done')),
                ('order_line.product_id', '=', delivery_product.id),
                ('select_deliver_date', '=', target),
            ]
            count = request.env['sale.order'].sudo().search_count(domain)
            remaining = max(capacity - count, 0) if capacity else 9999
            full = capacity and count >= capacity

            results.append({
                'date': target.strftime('%Y-%m-%d'),
                'remaining': remaining,
                'full': full,
            })

        # فقط ۵ روز اولی که ظرفیت دارند + روزهای بینشان را نگه داریم
        available_days = [r for r in results if not r['full']]
        if not available_days:
            return results[:5]  # همه پر؟ پس همان ۵ تا اول

        first_idx = results.index(available_days[0])
        shown = results[first_idx:first_idx + 10]  # مثلاً تا ۵ روز آزاد بعدی + بینشان
        return shown[:10]

    # @http.route('/shop/delivery_slot', type='json', auth='public', website=True, csrf=False)
    # def save_delivery_slot(self, date_str=None, slot=None):
    #     order = request.website.sale_get_order()
    #     if not order:
    #         return {'ok': False}
    #
    #     vals = {}
    #     if date_str:
    #         try:
    #             expected = datetime.strptime(date_str, '%Y-%m-%d').date()
    #             vals['select_deliver_date'] = expected
    #         except Exception:
    #             return {'ok': False, 'error': 'bad_date'}
    #
    #         carrier = order.carrier_id.sudo()
    #         capacity = carrier.daily_capacity or 0
    #         delivery_product = carrier.product_id
    #
    #         if capacity > 0:
    #             domain = [
    #                 ('state', 'in', ('sale', 'done')),
    #                 ('order_line.product_id', '=', delivery_product.id),
    #                 ('select_deliver_date', '=', expected),
    #             ]
    #             count = request.env['sale.order'].sudo().search_count(domain)
    #             if count >= capacity:
    #                 return {
    #                     'ok': False,
    #                     'error': 'capacity_reached',
    #                     'remaining': 0,
    #                     'taken': count,
    #                     'capacity': capacity,
    #                 }
    #
    #     if slot is not None:
    #         vals['delivery_slot'] = slot or False
    #
    #     if vals:
    #         order.sudo().write(vals)
    #     return {'ok': True}

    @http.route('/shop/delivery_slot', type='json', auth='public', website=True, csrf=False)
    def save_delivery_slot(self, date_str=None, slot=None):
        order = request.website.sale_get_order()
        if not order:
            return {'ok': False, 'error': 'no_order'}

        vals = {}

        # تاریخ الزامی است
        if not date_str:
            return {'ok': False, 'error': 'no_date'}

        try:
            expected = datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception:
            return {'ok': False, 'error': 'bad_date'}

        vals['select_deliver_date'] = expected

        if slot is not None:
            vals['delivery_slot'] = slot or 'morning'


        order.sudo().write(vals)
        _logger.info("Saved delivery date/slot on SO %s: %s", order.name, vals)
        return {'ok': True}
    @http.route('/shop/current_shipping_city', type='json', auth='public', website=True, csrf=False)
    def current_shipping_city(self):
        order = request.website.sale_get_order()
        partner = order.partner_shipping_id if order else request.env.user.partner_id
        # اگر فیلد city_id داری، اولویت بده؛ در غیر اینصورت city متنی
        city = (partner.city_id and partner.city_id.name) or (partner.city or '')
        return {'city': city}

class WebsiteSale(payment_portal.PaymentPortal):


    def _get_mandatory_billing_address_fields(self, country_sudo):

        field_names = super()._get_mandatory_billing_address_fields(country_sudo)
        field_names.discard('email')
        field_names.discard('zip')
        return field_names

    def _get_mandatory_shipping_address_fields(self, country_sudo):

        field_names = super()._get_mandatory_shipping_address_fields(country_sudo)
        field_names.discard('email')
        field_names.discard('zip')
        return field_names

    def _get_mandatory_address_fields(self, country_sudo):

        field_names = super()._get_mandatory_address_fields(country_sudo)
        field_names.discard('email')
        field_names.discard('zip')
        return field_names

    # @route(
    #     '/shop/address/submit', type='http', methods=['POST'], auth='public', website=True,
    #     sitemap=False
    # )
    # def shop_address_submit(
    #         self, partner_id=None, address_type='billing', use_delivery_as_billing=None, callback=None,
    #         required_fields=None, **form_data
    # ):
    #
    #
    #     required_field = required_fields
    #     if form_data['city'] == "تهران" and not form_data['partner_latitude']:
    #         required_field = "partner_latitude"
    #     res = super().shop_address_submit( partner_id=None, address_type='billing', use_delivery_as_billing=None, callback=None,
    #         required_fields=required_field, **form_data)
    #     order_sudo = request.website.sale_get_order()
    #     if partner_id:
    #         partner_id = request.env['res.partner'].sudo().browse(int(partner_id))
    #         partner_id.sudo().write({
    #             'partner_latitude':form_data['partner_latitude'] if form_data['partner_latitude'] else False ,
    #             'partner_longitude':form_data['partner_longitude'] if form_data['partner_longitude'] else False,
    #             'city_id': int(form_data['city_id']) or False,
    #                                     })
    #
    #     return res
    @http.route(
        '/shop/address/submit', type='http', methods=['POST'], auth='public', website=True, sitemap=False
    )
    def shop_address_submit(
            self, partner_id=None, address_type='billing', use_delivery_as_billing=None,
            callback=None, required_fields=None, **form_data
    ):
        # شرط ویژه برای تهران و موقعیت نقشه
        required_field = required_fields
        if form_data.get('city') == "تهران" and not form_data.get('partner_latitude'):
            required_field = "partner_latitude"

        # اجرای منطق اصلی اودو
        res = super().shop_address_submit(
            partner_id=partner_id,
            address_type=address_type,
            use_delivery_as_billing=use_delivery_as_billing,
            callback=callback,
            required_fields=required_field,
            **form_data
        )

        # دریافت سفارش جاری و پارتنر
        order_sudo = request.website.sale_get_order()
        partner_sudo = order_sudo.partner_id.sudo() if order_sudo else None
        submitted_partner = None

        # اگر آدرس خاصی ویرایش شده بود
        if partner_id:
            submitted_partner = request.env['res.partner'].sudo().browse(int(partner_id))

        # اگر آدرس جدید ساخته شد (در checkout)
        elif order_sudo and order_sudo.partner_shipping_id:
            submitted_partner = order_sudo.partner_shipping_id.sudo()

        if not submitted_partner:
            return res  # ایمنی

        # به‌روزرسانی آدرس جاری (مثلاً delivery)
        vals = {}
        if form_data.get('partner_latitude'):
            vals['partner_latitude'] = form_data['partner_latitude']
        if form_data.get('partner_longitude'):
            vals['partner_longitude'] = form_data['partner_longitude']
        if form_data.get('city_id'):
            vals['city_id'] = int(form_data['city_id'])
        if form_data.get('state_id'):
            vals['state_id'] = int(form_data['state_id'])
        if form_data.get('country_id'):
            vals['country_id'] = int(form_data['country_id'])
        if form_data.get('phone'):
            vals['phone'] = form_data['phone']

        if vals:
            submitted_partner.write(vals)

        # 🟢 حالا اگر پارتنر اصلی یا آدرس فاکتور تلفن/شهر/... خالی دارد، از این آدرس پر کن
        if partner_sudo:
            sync_vals = {}
            fields_to_sync = ['phone', 'city_id', 'state_id', 'country_id', 'partner_latitude', 'partner_longitude']
            for field in fields_to_sync:
                if not partner_sudo[field] and submitted_partner[field]:
                    sync_vals[field] = submitted_partner[field].id if hasattr(submitted_partner[field], 'id') else \
                    submitted_partner[field]
            if sync_vals:
                partner_sudo.write(sync_vals)

            # آدرس‌های فاکتور و تحویل را هم پر کن اگر خالی هستند
            for addr_type in ['partner_shipping_id', 'partner_invoice_id']:
                addr = getattr(order_sudo, addr_type, None)
                if addr:
                    addr_sync_vals = {}
                    for field in fields_to_sync:
                        if not addr[field] and submitted_partner[field]:
                            addr_sync_vals[field] = (
                                submitted_partner[field].id
                                if hasattr(submitted_partner[field], 'id')
                                else submitted_partner[field]
                            )
                    if addr_sync_vals:
                        addr.write(addr_sync_vals)

        return res



class StockBarcodeController(CoreBarcodeController):

    def _try_open_pack_by_lot(self, lot_name):
        if not lot_name:
            return False
        env = request.env
        pack_types = env["stock.warehouse"].search([]).mapped("pack_type_id")
        if not pack_types:
            return False

        lot = env["stock.lot"].search([("name", "=", lot_name)], limit=1)
        if not lot:
            return False

        mls = env["stock.move.line"].search([
            ("lot_id", "=", lot.id),
            ("picking_id.picking_type_id", "in", pack_types.ids),
            ("picking_id.state", "in", ("assigned", "confirmed", "waiting")),
        ], limit=1)
        if not mls:
            return False

        picking = mls.picking_id

        action = request.env["ir.actions.actions"]._for_xml_id(
            "stock_barcode.stock_barcode_picking_client_action"
        )

        # --- فیکس اینجاست ---
        ctx = action.get("context") or {}
        if isinstance(ctx, str):
            ctx = safe_eval(ctx)  # تبدیل رشته‌ی context به dict امن

        # حالا می‌تونی با خیال راحت آپدیت کنی
        ctx.update({
            "active_model": "stock.picking",
            "active_id": picking.id,
            "active_ids": [picking.id],
            "default_picking_id": picking.id,
            "picking_id": picking.id,
        })

        action["context"] = ctx
        return {'action': action}

    @http.route("/stock_barcode/scan_from_main_menu", type="json", auth="user")
    def main_menu(self, barcode):
        env = request.env
        barcode_type = None
        nomenclature = env.company.nomenclature_id
        parsed_results = nomenclature.parse_barcode(barcode)

        if parsed_results and nomenclature.is_gs1_nomenclature:
            for result in parsed_results[::-1]:
                if result["rule"].type == "lot":
                    lot_code = result.get("value") or result.get("code") or barcode
                    ret_open_pack = self._try_open_pack_by_lot(lot_code)
                    if ret_open_pack:
                        return ret_open_pack
                    barcode_type = "lot"
                    break
        elif parsed_results:
            barcode = parsed_results.get("code", barcode)

        if barcode_type is None:
            ret_open_pack = self._try_open_pack_by_lot(barcode)
            if ret_open_pack:
                return ret_open_pack

        # ادامه: همان رفتار پیش‌فرض
        if not barcode_type:
            ret_open_picking = self._try_open_picking(barcode)
            if ret_open_picking:
                return ret_open_picking

            ret_open_picking_type = self._try_open_picking_type(barcode)
            if ret_open_picking_type:
                return ret_open_picking_type

        if env.user.has_group("stock.group_stock_multi_locations") and \
           (not barcode_type or barcode_type in ["location", "dest_location"]):
            ret_new_internal_picking = self._try_new_internal_picking(barcode)
            if ret_new_internal_picking:
                return ret_new_internal_picking

        if not barcode_type or barcode_type == "product":
            ret_open_product_location = self._try_open_product_location(barcode)
            if ret_open_product_location:
                return ret_open_product_location

        if env.user.has_group("stock.group_production_lot") and \
           (not barcode_type or barcode_type == "lot"):
            ret_open_lot = self._try_open_lot(barcode)
            if ret_open_lot:
                return ret_open_lot

        if env.user.has_group("stock.group_tracking_lot") and \
           (not barcode_type or barcode_type == "package"):
            ret_open_package = self._try_open_package(barcode)
            if ret_open_package:
                return ret_open_package

        if env.user.has_group("stock.group_stock_multi_locations"):
            return {"warning": _("No picking or location or product corresponding to barcode %(barcode)s", barcode=barcode)}
        else:
            return {"warning": _("No picking or product corresponding to barcode %(barcode)s", barcode=barcode)}

class WebsiteSaleDynamicETA(WebsiteSale):

    # @http.route('/shop/states', type='json', auth='public', website=True, csrf=False)
    # def shop_states(self, country_code='IR', **kw):
    #     Country = request.env['res.country'].sudo()
    #     State = request.env['res.country.state'].sudo()
    #     country = Country.search([('code', '=', country_code)], limit=1)
    #     if not country:
    #         return []
    #     states = State.search([('country_id', '=', country.id)], order='name asc')
    #     return [{'id': s.id, 'name': s.name} for s in states]




    @http.route(['/shop/checkout'], type='http', auth='public', website=True, sitemap=False)
    def shop_checkout(self, **post):
        order = request.website.sale_get_order()
        if order:
            order.sudo()._compute_expected_date()  # ← بازمحاسبه همین‌جا
        return super().shop_checkout(**post)