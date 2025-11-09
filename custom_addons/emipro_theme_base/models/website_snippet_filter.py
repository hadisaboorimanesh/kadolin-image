# -*- coding: utf-8 -*-

import datetime
from collections import Counter

from odoo import models, fields, api, _
from odoo.osv import expression
from datetime import datetime, timedelta


class WebsiteSnippetFilter(models.Model):
    _inherit = 'website.snippet.filter'

    _MODEL_PRODUCT_PRODUCT = 'product.product'

    def _filter_records_to_values(self, records, is_sample=False):
        res_products = super()._filter_records_to_values(records, is_sample)
        if self.model_name == self._MODEL_PRODUCT_PRODUCT:
            context_flags = ['add2cart', 'compare', 'wishlist', 'rating', 'quickview', 'color_swatches',
                             'image_flipper', 'product_label']

            for flag in context_flags:
                if self.env.context.get(flag):
                    res_products = [{**d, flag: True} for d in res_products]

        if self.model_name in ['product.public.category', 'product.brand']:
            if self.env.context.get('count'):
                res_products = [{**d, 'count': True} for d in res_products]
        return res_products

    def _get_products_discount_products(self, website, limit, domain, **kwargs):
        products = []
        price_list = website._get_current_pricelist()
        pl_items = price_list.item_ids.filtered(lambda r: (
                (not r.date_start or r.date_start <= datetime.datetime.today()) and (
                not r.date_end or r.date_end > datetime.datetime.today())))
        products_ids = []
        if pl_items.filtered(lambda r: r.applied_on in ['3_global']):
            products = self.env[self._MODEL_PRODUCT_PRODUCT].with_context(display_default_code=False,
                                                                          add2cart_rerender=True).search(domain,
                                                                                                         limit=limit)
        else:
            product_product = self.env[self._MODEL_PRODUCT_PRODUCT].search([])
            for line in pl_items:
                if line.applied_on in ['1_product']:
                    products = product_product.filtered(lambda l: l.id in line.product_tmpl_id.product_variant_ids.ids)
                elif line.applied_on in ['2_product_category']:
                    products = product_product.filtered(lambda l: l.categ_id.id in line.categ_id.ids)
            products_ids = products and list(set(products.ids)) or []
        if products_ids:
            domain = expression.AND([domain, [('id', 'in', products_ids)]])
            products = self.env[self._MODEL_PRODUCT_PRODUCT].with_context(display_default_code=False,
                                                                          add2cart_rerender=True).search(domain,
                                                                                                         limit=limit)
        return products

    def _get_products_top_sold_products(self, website, limit, domain, **kwargs):
        today = datetime.today()
        last_days = today - timedelta(days=website.top_sold_days or 30)
        last_days = last_days.strftime("%Y-%m-%d %H:%M:%S")
        products = []

        sale_lines = self.env['sale.order.line'].search([('state', 'in', ['sale', 'done']),
                                                         ('create_date', '>=', last_days),('is_storable','!=',False)])

        if not sale_lines:
            return products

        product_sales = {}
        for line in sale_lines:
            product_sales[line.product_id.id] = product_sales.get(line.product_id.id, 0) + line.product_uom_qty

        top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:limit]
        products_ids = [p[0] for p in top_products]

        if products_ids:
            domain = expression.AND([domain, [('id', 'in', products_ids)]])
            products = self.env[self._MODEL_PRODUCT_PRODUCT].with_context(display_default_code=False,
                                                                          add2cart_rerender=True).search(domain,
                                                                                                         limit=limit)
        return products
