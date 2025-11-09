# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.http import request
from odoo.tools import lazy

_MODEL_PRODUCT_TAB_LINE = 'product.tab.line'

class ProductTemplate(models.Model):
    _inherit = "product.template"

    tab_line_ids = fields.One2many(_MODEL_PRODUCT_TAB_LINE, 'product_id', 'Product Tabs',
                                   compute="_get_product_tabs",
                                   inverse="_set_product_tabs", help="Set the product tabs")
    product_brand_id = fields.Many2one('product.brand', string='Brand', help='Brand for this product')

    def write(self, vals):
        tab_lines = vals.get('tab_line_ids')
        if tab_lines:
            TabLine = self.env[_MODEL_PRODUCT_TAB_LINE]
            for value in tab_lines:
                operation, tab_id_or_str, tab_data = value

                if isinstance(tab_id_or_str, int):
                    tab_line = TabLine.browse(tab_id_or_str)

                    if operation == 1 and tab_line.tab_type == 'global':
                        websites_ids = tab_line.website_ids.ids or []
                        vals_tab = {
                            'is_modified': True,
                            'parent_id': tab_line.id,
                            'product_id': self.id,
                            'tab_type': 'specific product',
                            'tab_content': tab_data.get('tab_content') or tab_line.tab_content,
                            'sequence': tab_line.sequence,
                            'website_ids': [[6, 0, websites_ids]],
                        }
                        TabLine.create(vals_tab)

                    elif operation == 2 and tab_line.tab_type != 'global':
                        tab_line.unlink()

                elif isinstance(tab_id_or_str, str) and operation == 0:
                    tab_data.update({'product_id': self.id})
                    TabLine.create(tab_data)

        return super(ProductTemplate, self).write(vals)

    def _get_product_tabs(self):
        for product in self:
            all_global_product_tabs = self.env[_MODEL_PRODUCT_TAB_LINE].search(
                [('tab_type', '=', 'global')])
            product_tabs = self.env[_MODEL_PRODUCT_TAB_LINE].search([('product_id', '=', self.id)])
            all_products_tabs = all_global_product_tabs + product_tabs
            product_tabs = all_products_tabs.ids
            for product_tab in all_products_tabs:
                if product_tab.is_modified == True and product_tab.product_id.id == self.id and product_tab.parent_id:
                    if product_tab.parent_id.id in product_tabs:
                        product_tabs.remove(product_tab.parent_id.id)

            product.tab_line_ids = [(6, 0, product_tabs)]

    def _set_product_tabs(self):
        return True

    def remove_cart_button(self):
        return self.sudo().out_of_stock()

    @api.model
    def _get_website_accessory_product_filter(self):
        return self.env.ref('website_sale.dynamic_filter_cross_selling_accessories').id

    def _get_attrib_values_domain(self, attribute_values):
        res = super()._get_attrib_values_domain(attribute_values=attribute_values)

        brand_ids = []
        for value in attribute_values:
            if value[0] == 0:
                brand_ids.append(value[1])
        if brand_ids:
            res.append([('product_brand_id', 'in', brand_ids)])

        return res

    def out_of_stock(self):
        stock = 0
        for product in self.product_variant_ids:
            stock += product.sudo().with_context(warehouse=request.website.warehouse_id.id).free_qty
        if self.type == 'consu' and self.is_storable == True and not self.allow_out_of_stock_order and stock < 1:
            return True
        return False

    def get_slider_product_price(self):
        website = request.env['website'].get_current_website()
        products_prices = lazy(lambda: self._get_sales_prices(website))
        return products_prices

    def check_stock_availability_message(self):
        stock = 0
        for product in self.product_variant_ids:
            stock += product.sudo().with_context(warehouse=request.website.warehouse_id.id).free_qty
        return int(stock) if self.show_availability and int(stock) < self.available_threshold else False

    def get_previous_product(self):
        previous_product_tmpl = self.sudo().search([('website_sequence', '<', self.website_sequence),
                                                    ('website_published', '=', self.website_published), ],
                                                   order='website_sequence DESC', limit=1)
        return previous_product_tmpl or False

    def get_next_prodcut(self):
        next_prodcut_tmpl = self.sudo().search([('website_sequence', '>', self.website_sequence),
                                                ('website_published', '=', self.website_published), ],
                                               order='website_sequence ASC', limit=1)

        return next_prodcut_tmpl or False
