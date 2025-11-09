# -*- coding: utf-8 -*-

#######################################################################################
# Emipro Theme Base Module Manifest File.
#
# This file contains the metadata for the Emipro Theme Base module, including:
#     - Module name, version, and category
#     - Summary and description
#     - Author and license information
#     - Dependencies on other modules
#     - Data, demo, and security files to load
#     - Application, install, and auto-install flags
#
# Odoo uses this file to identify, install, and manage the module.
#######################################################################################

{
    # Theme information
    'name': 'Emipro Theme Base',
    'category': 'Base',
    'summary': 'Base module containing common libraries for all Emipro eCommerce themes.',
    'version': '18.0.0.25',
    'license': 'OPL-1',
    'depends': ["website_sale_stock", "website_sale_comparison_wishlist", "web_editor",
                "im_livechat", "website_blog", ],

    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/website.xml',
        'views/synonym_group.xml',
        'views/website_menu_view.xml',
        'views/search_keyword_report.xml',
        'views/product_attribute.xml',
        'views/product_tabs.xml',
        'views/product_template.xml',
        'views/product_public_category.xml',
        'views/product_pricelist.xml',
        'views/product_pricelist_item.xml',
        'views/product_brand.xml',
        'views/menu_label.xml',
        'views/product_label.xml',
        'views/mobile_header_icon.xml',
        'wizards/product_brand_wizard_view.xml',
        'wizards/product_label_wizard_view.xml',
        'templates/assets.xml',
        'templates/template.xml',
        'templates/pwa.xml',
        'templates/offilne.xml',
        'views/product_measure_attributes.xml',
    ],

    'assets': {
        'web.assets_frontend': [
            'emipro_theme_base/static/src/snippets/s_dynamic_snippet_brand/000.js',
            'emipro_theme_base/static/src/snippets/s_dynamic_snippet_product_template/000.js',
            'emipro_theme_base/static/src/snippets/s_dynamic_snippet_category/000.js',
            'emipro_theme_base/static/src/js/frontend/lazy_load.js',
            'emipro_theme_base/static/src/js/frontend/loadmore.js',
            'emipro_theme_base/static/src/js/frontend/website_sale.js',
            'emipro_theme_base/static/src/js/frontend/pwa_web.js',
            'emipro_theme_base/static/src/js/frontend/price_table.js',
        ],
        'web_editor.assets_wysiwyg': [],
        'website.assets_editor': [],
    },

    # Author
    'author': 'Emipro Technologies Pvt. Ltd.',
    'website': 'https://www.emiprotechnologies.com',
    'maintainer': 'Emipro Technologies Pvt. Ltd.',
    'images': [
        'static/description/emipro_theme_base.jpg',
    ],
    # Technical
    'installable': True,
    'auto_install': False,
    'price': 50.00,
    'currency': 'USD',
}
