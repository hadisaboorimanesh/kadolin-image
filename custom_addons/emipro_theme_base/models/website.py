# -*- coding: utf-8 -*-

import base64
import json
import werkzeug.urls
from urllib.parse import urlparse, parse_qs, urlencode

from odoo.osv import expression
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.addons.auth_oauth.controllers.main import OAuthLogin


class Website(models.Model):
    _inherit = "website"

    # Advanced search
    enable_smart_search = fields.Boolean(
        string="Advanced Search", default=True,
        help="Enable it to activate search synonyms and search keywords reporting.")
    search_in_brands = fields.Boolean(string="Search with Brands", default=True)
    search_in_attributes_and_values = fields.Boolean(string="Search with Attributes", default=True)

    # Load More
    is_load_more = fields.Boolean(string='Load More', help="Load more will be enabled")
    load_more_image = fields.Binary('Load More Image', help="Display this image while load more applies.")
    button_or_scroll = fields.Selection([
        ('automatic', 'Automatic- on page scroll'),
        ('button', 'Button- on click button')
    ], string="Loading type for products", required=True, default='automatic')
    prev_button_label = fields.Char(string='Label for the Prev Button',
                                    default="Load prev", translate=True)
    next_button_label = fields.Char(string='Label for the Next Button',
                                    default="Load next", translate=True)

    # B2B Feature
    b2b_hide_add_to_cart = fields.Boolean('Hide Add to Cart Feature')
    b2b_hide_price = fields.Boolean('Hide Product Price')
    is_b2b_message = fields.Boolean('Display Message?')
    text_b2b_hide_details = fields.Char('Text for Details', default='to view price', translate=True)
    is_lazy_load = fields.Boolean(string='Lazyload', help="Lazy load will be enabled")
    lazy_load_image = fields.Binary('Lazyload Image', help="Display this image while lazy load applies.")

    # Allow selected countries
    allow_countries = fields.Many2many('res.country', string='Allow Countries')
    default_country_id = fields.Many2one('res.country', string='Default Country')
    homepage_id = fields.Many2one('website.page', string='Homepage')

    # OUT of STOCK settings
    option_out_of_stock = fields.Boolean('Display Label on Out of Stock Products',
                                         help="If Yes, then message/text will be displayed for out of stock products "
                                              "on shop page")
    text_out_of_stock = fields.Char('Out of Stock Label Text', default='OUT OF STOCK', translate=True)
    display_out_of_stock = fields.Boolean('Display Out of Stock Products', default=True)
    show_stock_filter = fields.Boolean('Show Stock Filter in Shop Page', default=True)

    # Progressive Web App(PWA)
    is_pwa = fields.Boolean('PWA', readonly=False, help="Enable Progressive Web Application")
    pwa_name = fields.Char(string='Name', readonly=False,
                           help="It will be used in the splash screen and Add To Home Screen’ pop-up.")
    pwa_short_name = fields.Char(string='Short Name', readonly=False,
                                 help="It will be used in a browser pop-up and the app shortcut name.")
    pwa_theme_color = fields.Char(string='Theme Color', readonly=False,
                                  help="The color is used to customize the look of the browser.")
    pwa_bg_color = fields.Char(string='Background Color', readonly=False,
                               help="The color used to customize the splash screen when launching from the home screen shortcut.")
    pwa_start_url = fields.Char(string='Start URL', readonly=False,
                                help="This is the URL on which the user will be landed when they add this app to the home screen and click on it.")
    app_image_512 = fields.Binary(string='Application Image(512x512)', readonly=False, store=True,
                                  help="It will be used in an app launcher, home screen, splash screen icons. (Required 512x512)")
    pwa_shortcuts_ids = fields.One2many('pwa.app.shortcut.ept', 'website_id', string='PWA Shortcuts')
    # Progressive Web App(PWA)

    # See All
    see_all = fields.Boolean('See All', default=True)
    show_attr_value = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
                                       'Total Attributes Value', default='4')

    is_free_shipping = fields.Boolean('Display free shipping offer in cart', default=False)
    free_shipping_price = fields.Integer('Free Shipping Price')
    is_card_layout = fields.Boolean('Display the product card layout.', default=False)
    top_sold_days = fields.Integer(string='Top-Selling Products Timeframe (Days)',
                                   help='Specify the number of days to consider when calculating top-selling products.')

    @api.onchange('display_out_of_stock')
    def _onchange_display_out_of_stock(self):
        if not self.display_out_of_stock:
            self.show_stock_filter = False
            self.option_out_of_stock = False

    @api.onchange('is_load_more')
    def _onchange_icon_load_more(self):
        if self.is_load_more:
            img_path = tools.misc.file_path('emipro_theme_base/static/src/img/loadmore.gif')
            with tools.misc.file_open(img_path, 'rb') as f:
                self.load_more_image = base64.b64encode(f.read())

    @api.onchange('is_lazy_load')
    def _onchange_icon_lazy_load(self):
        if self.is_lazy_load:
            img_path = tools.misc.file_path('emipro_theme_base/static/src/img/lazyload.gif')
            with tools.misc.file_open(img_path, 'rb') as f:
                self.lazy_load_image = base64.b64encode(f.read())

    def _search_with_fuzzy(self, search_type, search, limit, order, options):
        curr_website = self.env['website'].get_current_website()
        search_synonyms = False
        count, results, fuzzy_term = 0, [], False
        if search and curr_website.enable_smart_search:
            synonym_groups = self.env['synonym.group'].sudo().search([('website_id', 'in', [curr_website.id, False])])
            if synonym_groups:
                for synonym_group in synonym_groups:
                    synonyms = [synm.strip().lower() for synm in synonym_group.name.split(',')]
                    if search.strip().lower() in synonyms:
                        search_synonyms = synonyms
                        break
            if search_synonyms:
                for search in search_synonyms:
                    fuzzy_term = False
                    search_details = self._search_get_details(search_type, order, options)
                    if search and options.get('allowFuzzy', True):
                        fuzzy_term = self._search_find_fuzzy_term(search_details, search)
                        if fuzzy_term:
                            new_count, new_results = self._search_exact(search_details, fuzzy_term, limit, order)
                            if fuzzy_term.lower() == search.lower():
                                fuzzy_term = False
                        else:
                            new_count, new_results = self._search_exact(search_details, search, limit, order)
                    else:
                        new_count, new_results = self._search_exact(search_details, search, limit, order)

                    for new_res in new_results:
                        if new_res not in results:
                            res = [res for res in results if res['model'] == new_res['model']]
                            if res:
                                for prod in new_res['results']:
                                    if prod not in res[0]['results']:
                                        res[0]['results'] += prod
                                        res[0]['count'] += 1
                                        count += 1
                            else:
                                results.append(new_res)
                                count += new_res['count']
            else:
                count, results, fuzzy_term = super()._search_with_fuzzy(search_type, search, limit,
                                                                        order, options)
        else:
            count, results, fuzzy_term = super()._search_with_fuzzy(search_type, search, limit,
                                                                    order, options)
        return count, results, fuzzy_term

    @api.onchange('b2b_hide_price')
    def _onchange_b2b_hide_price(self):
        if self.b2b_hide_price:
            self.b2b_hide_add_to_cart = True

    @api.constrains('b2b_hide_price', 'b2b_hide_add_to_cart', 'is_b2b_message')
    def _check_b2b_message(self):
        for rec in self:
            if rec.is_b2b_message and not (rec.b2b_hide_price or rec.b2b_hide_add_to_cart):
                raise ValidationError(
                    _('You cannot enabled "Display Message?" without using "Hide Add to Cart" or "Hide Product Price".'))

    def display_add_to_cart(self):
        check_hide_add_to_cart = False if self.is_public_user() and self.b2b_hide_add_to_cart else True
        return check_hide_add_to_cart

    def display_product_price(self):
        check_hide_price = False if self.is_public_user() and self.b2b_hide_price else True
        return check_hide_price

    def display_b2b_message(self):
        display_message = True if self.is_public_user() and self.is_b2b_message else False
        return display_message

    @staticmethod
    def _get_product_sort_mapping_ept():
        return [('discount asc', _('Discount'))]

    def get_all_product_template_filter(self):
        return self.env.ref('website_sale.dynamic_filter_newest_products').id

    def get_all_product_public_category_template_filter(self):
        return self.env.ref('emipro_theme_base.dynamic_filter_category').id

    def get_all_product_brand_template_filter(self):
        return self.env.ref('emipro_theme_base.dynamic_filter_brand').id

    def _search_get_details(self, search_type, order, options):
        result = super()._search_get_details(search_type=search_type, order=order, options=options)

        if search_type == 'products_only':
            base_domain = result[0]['base_domain'][0]

            def add_domain(extra):
                """Helper to safely merge domains."""
                nonlocal base_domain
                base_domain = expression.AND([base_domain, extra])

            # BRAND SPECIFIC PAGE
            brand = options.get('brand')
            if brand:
                add_domain([('product_brand_id', '=', brand.id)])

            # OUT OF STOCK
            if options.get('out_of_stock'):
                add_domain(expression.OR([
                    [('product_variant_ids.free_qty', '>', 0)],
                    [('allow_out_of_stock_order', '=', True)]
                ]))

            # BRAND FILTER via request_args
            request_args = options.get('request_args', [])
            brand_ids = [int(v.split("-")[1]) for v in request_args if v and v.startswith("0-")]
            if brand_ids:
                add_domain([('product_brand_id', 'in', brand_ids)])

            result[0]['base_domain'][0] = base_domain

        return result

    def list_providers_ept(self):
        """
            This method is used for return the encoded url for the auth providers
            :return: link for the auth providers.
            Added by: Shubham Kumar
            Date: 15 Oct 2024
        """
        try:
            providers = request.env['auth.oauth.provider'].sudo().search_read([('enabled', '=', True)])
        except Exception:
            providers = []
        for provider in providers:
            return_url = request.httprequest.url_root + 'auth_oauth/signin'
            state = OAuthLogin.get_state(self, provider)
            params = dict(
                response_type='token',
                client_id=provider['client_id'],
                redirect_uri=return_url,
                scope=provider['scope'],
                state=json.dumps(state),
            )
            provider['auth_link'] = "%s?%s" % (provider['auth_endpoint'], werkzeug.urls.url_encode(params))
        return providers

    def get_remove_url(self, url, option, values):
        vals = {}
        shop_url = url
        if option == 'attribute':
            attribute_values = list(filter(lambda l: l[0] != 0, values))
            attribute_dict = {}
            if attribute_values:
                attributes = {v[0] for v in attribute_values}
                attribute_obj = self.env['product.attribute'].sudo()
                attribute_value_obj = self.env['product.attribute.value'].sudo()
                for attribute in attributes:
                    attribute_dict[attribute_obj.browse(attribute)] = []
                for value in attribute_values:
                    current_url = shop_url
                    option_value = '-'.join(str(num) for num in value)
                    attr_url = current_url.replace(f"attribute_value={option_value}", '')
                    attribute_id = attribute_obj.browse(value[0])
                    attribute_value = attribute_value_obj.browse(value[1])
                    attribute_dict[attribute_id].append({
                        attribute_value: attr_url
                    })
                vals.update(attribute_details=attribute_dict)
            brand_values = list(filter(lambda l: l[0] == 0, values))
            if brand_values:
                brand_details = []
                brand_obj = self.env['product.brand'].sudo()
                for value in brand_values:
                    current_url = shop_url
                    option_value = '-'.join(str(num) for num in value)
                    brand_url = current_url.replace(f"attrib={option_value}", '')
                    brand_id = brand_obj.browse(value[1])
                    brand_details.append({
                        brand_id: brand_url
                    })
                vals.update(brand_details=brand_details)
        if option == 'tag':
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            tags_values = query_params.get('tags', [])
            tag_obj = self.env['product.tag'].sudo()
            tag_details = []
            for value in tags_values:
                current_url = shop_url
                tag_url = current_url.replace(f"tags={value}", "")
                tag_id = tag_obj.browse(int(value))
                tag_details.append({
                    tag_id: tag_url
                })
            vals.update(tag_details=tag_details)
        return vals

    def get_attribute_clear_url(self, url, attribute_id):
        # prepare url
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        query_params['attribute_value'] = [value for value in query_params.get('attribute_value', []) if
                                           f'{attribute_id.id}-' not in value]
        if f"attribute_value={attribute_id.id}-" in url:
            new_url = parsed_url._replace(query=urlencode(query_params, doseq=True)).geturl()
            return new_url

    def get_clear_brand_url(self, url):
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        query_params['attribute_value'] = [value for value in query_params.get('attribute_value', []) if
                                           '0-' not in value]
        if "attribute_value=0-" in url:
            new_url = parsed_url._replace(query=urlencode(query_params, doseq=True)).geturl()
            return new_url

        return None

    def get_clear_tag_url(self, url):
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        query_params.pop('tags', None)
        if "tags" in url:
            new_url = parsed_url._replace(query=urlencode(query_params, doseq=True)).geturl()
            return new_url
        return None

    @api.model
    def pager(self, url, total, page=1, step=30, scope=5, url_args=None):
        if 'brand' in url_args:
            url = "/shop/brands/%s" % request.env['ir.http']._slug(url_args['brand'])

        if 'brand' in url_args:
            url_args.pop('brand')

        res = super().pager(url=url, total=total, page=page, step=step, scope=scope, url_args=url_args)

        return res
