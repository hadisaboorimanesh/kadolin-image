# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.http import request


class WebsiteMenu(models.Model):
    _inherit = 'website.menu'

    dynamic_mega_menu = fields.Boolean(string="Dynamic Mega Menu", inverse='_set_field_is_mega_menu_overrided')
    category_selection = fields.Selection([('all', 'All Categories'), ('specific', 'Specific Category')],
                                          'Category Selection', default='specific',
                                          inverse='_set_field_is_mega_menu_overrided')
    ecom_category = fields.Many2many('product.public.category', string='Select Category',
                                     inverse='_set_field_is_mega_menu_overrided')
    category_menu_styles = fields.Selection([('style1', 'Style 1'),
                                             ('style2', 'Style 2'),
                                             ('style3', 'Style 3'),
                                             ('style4', 'Style 4'),
                                             ('style5', 'Style 5'),
                                             ('style6', 'Nested menu'),
                                             ('style7', 'Style 7'),
                                             ('style8', 'Style 8'),
                                             ('style9', 'Style 9')], 'Mega Menu Style',
                                            inverse='_set_field_is_mega_menu_overrided')
    menu_label_id = fields.Many2one('menu.label', string='Menu Label', help='Select a menu label for this category')
    is_highlight_menu = fields.Boolean(string="Highlight Menu")
    website_id = fields.Many2one('website', 'Website', ondelete='cascade', inverse='_set_field_is_mega_menu_overrided')
    mega_menu_content = fields.Html(translate=True)
    product_brand_ids = fields.Many2many('product.brand', string='Select Brands', help="You can "
                                                                                       "set "
                                                                                       "product "
                                                                                       "brands on mega menu style 1.")
    mega_menu_content_ids = fields.One2many("mega.menu.content", 'website_menu_id', string="website menu")
    product_template_ids = fields.Many2many('product.template', string='Select Products', help="You can "
                                                                                               "set "
                                                                                               "product "
                                                                                               "on mega menu style 8.")

    @api.model
    def get_tree(self, website_id, menu_id=None):
        website = self.env['website'].browse(website_id)

        def make_tree(node):
            is_homepage = bool(node.page_id and website.homepage_id.id == node.page_id.id)
            menu_url = node.page_id.url if node.page_id else node.url
            menu_node = {
                'fields': {
                    'id': node.id,
                    'name': node.name,
                    'url': menu_url,
                    'new_window': node.new_window,
                    'is_mega_menu': node.is_mega_menu,
                    'sequence': node.sequence,
                    'parent_id': node.parent_id.id,
                    'dynamic_mega_menu': node.dynamic_mega_menu,
                },
                'children': [],
                'is_homepage': is_homepage,
            }
            for child in node.child_id:
                menu_node['children'].append(make_tree(child))
            return menu_node

        menu = menu_id and self.browse(menu_id) or website.menu_id
        return make_tree(menu)

    def _set_field_is_mega_menu_overrided(self):
        for menu in self:
            if not menu.is_mega_menu:
                menu.mega_menu_content = False
                menu.mega_menu_classes = False
                continue

            if not menu.dynamic_mega_menu:
                if not menu.mega_menu_content:
                    menu.mega_menu_content = self.env['ir.ui.view']._render_template(
                        'website.s_mega_menu_odoo_menu'
                    )
                continue

            website_id = menu.website_id.id or request.env['website'].sudo().get_current_website().id
            context = {
                'category_menu_styles': menu.category_menu_styles,
                'menu': menu,
                'website_id': website_id
            }
            template = 'theme_clarico_vega.dynamic_category_mega_menu'
            translations = {}

            for lang_code, _ in (self.env['res.lang'].get_installed() or [('en_US', '')]):
                with self.env.cr.savepoint():
                    ctx = dict(self.env.context, lang=lang_code)
                    mega_menu_html = self.env['ir.ui.view'].with_context(ctx)._render_template(template, values=context)
                    translations[lang_code] = mega_menu_html

            menu.update_field_translations('mega_menu_content', translations)
