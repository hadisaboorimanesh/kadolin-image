# -*- coding: utf-8 -*-
{
    'name': "Website Sale Limit Product Quantity",

    'summary': """Limit Max. & Min. Ordered Qty. per Customer""",

    'description': """Limit Max. & Min. Ordered Qty. per Customer""",

    'author': "Azkob",
    'category': 'eCommerce',
    'version': '1.0',
    'website': 'https://www.azkob.com/',
    # any module necessary for this one to work correctly
    'depends': ['website_sale_stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'data/ir_cron.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            '/website_sale_limit_product_qty/static/src/js/limit_error.js',
        ]
    },
    # only loaded in demonstration mode
    'demo': [
    ],

    'installable': True,
    'application': True,
    'price': 50,
    'currency': 'EUR',
    'images': ['static/description/banner.jpg'],
    'live_test_url': "https://youtu.be/3GX-GAjk0dA",
}
