# -*- coding: utf-8 -*-

#######################################################################################
# Theme Clarico Vega Module Manifest File.
#
# This file contains the metadata for the Theme Clarico Vega module, including:
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
    'name': 'Theme Clarico Vega',
    'category': 'Theme/eCommerce',
    'summary': 'An Odoo eCommerce Solution with a lot of well-analized features. Suitable for all kind of eCommerce Businesses like Furniture, Fashion, Electronics, Beauty, Fitness, Jewelry, etc.',
    'version': '18.0.0.39',
    'license': 'OPL-1',
    'depends': ['emipro_theme_base', 'website_mass_mailing', ],

    'data': [
        'templates/theme_customise_option.xml',
        'templates/header.xml',
        'templates/quick_view.xml',
        'templates/shop.xml',
        'templates/product.xml',
        'templates/brand_listing.xml',
        'templates/cart.xml',
        'templates/mega_menu.xml',
        'templates/login_popup.xml',
        'templates/snippets.xml',
        'templates/dynamic_slider/dynamic_slider_brand.xml',
        'templates/dynamic_slider/dynamic_slider_category.xml',
        'templates/footer.xml',
        'templates/see_all.xml',
        'templates/wishlist.xml',
        'templates/compare.xml',
        'templates/cart_popover.xml',
        'templates/product_label.xml',
        'templates/brand_page.xml',
        'templates/wishlist_collection_templates.xml',
        'templates/emipro_custom_snippets.xml',
        'templates/image_hotspot_popup.xml',
    ],

    'assets': {
        "portal.assets_chatter_style": [
            'theme_clarico_vega/static/src/scss/product_rating_design.scss',
        ],
        'web._assets_frontend_helpers': [
            'theme_clarico_vega/static/lib/para_size.scss',
        ],
        'web.assets_frontend': [
            'theme_clarico_vega/static/src/scss/mixins.scss',
            'theme_clarico_vega/static/src/scss/header.scss',
            'theme_clarico_vega/static/src/scss/search.scss',
            'theme_clarico_vega/static/src/scss/button_style.scss',
            'theme_clarico_vega/static/src/scss/quick_view.scss',
            'theme_clarico_vega/static/src/scss/product.scss',
            'theme_clarico_vega/static/src/scss/owl.carousel.min.css',
            'theme_clarico_vega/static/src/js/frontend/**',
            'theme_clarico_vega/static/src/scss/shop.scss',
            'theme_clarico_vega/static/src/scss/brand_listing.scss',
            'theme_clarico_vega/static/src/scss/cart.scss',
            'theme_clarico_vega/static/src/scss/megamenu.scss',
            'theme_clarico_vega/static/src/scss/compare.scss',
            'theme_clarico_vega/static/src/scss/snippets.scss',
            'theme_clarico_vega/static/src/scss/footer.scss',
            'theme_clarico_vega/static/src/scss/login_popup.scss',
            'theme_clarico_vega/static/src/scss/wishlist.scss',
            'theme_clarico_vega/static/src/xml/cart_notification.xml',
            'theme_clarico_vega/static/src/scss/sale_label.scss',
            'theme_clarico_vega/static/src/scss/static_snippet.scss',
            'theme_clarico_vega/static/src/scss/image_hotspot_design.scss',
            'theme_clarico_vega/static/src/xml/search_sidebar.xml',
        ],
        'website.assets_wysiwyg': [
            ('include', 'web._assets_helpers'),
            'theme_clarico_vega/static/src/xml/website.editor.xml',
            'theme_clarico_vega/static/src/js/editor/snippets.editor.js',
            'theme_clarico_vega/static/src/snippets/s_dynamic_snippet_brand/options.js',
            'theme_clarico_vega/static/src/snippets/s_dynamic_snippet_category/options.js',
            'theme_clarico_vega/static/src/js/editor/snippet.options.js',
            'theme_clarico_vega/static/src/js/editor/jquery-ui.min.js',
            'theme_clarico_vega/static/src/snippets/s_dynamic_snippet_product_template/options.js',
            'theme_clarico_vega/static/src/js/website_sale_editor.js',
        ],
        'web_editor.assets_wysiwyg': [
            'theme_clarico_vega/static/src/js/offer_wysiwyg.js',
        ],
    },

    # Author
    'author': 'Emipro Technologies Pvt. Ltd.',
    'website': 'https://www.emiprotechnologies.com',
    'maintainer': 'Emipro Technologies Pvt. Ltd.',
    'live_test_url': 'https://claricovega.theme18.demo.emiprotechnologies.com/',
    'images': [
        'static/description/main_poster.jpg',
        'static/description/main_screenshot.gif',
    ],

    # Technical
    'installable': True,
    'auto_install': False,
    'price': 249.00,
    'currency': 'USD',
}
