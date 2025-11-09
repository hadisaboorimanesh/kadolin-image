# -*- coding: utf-8 -*-
{
    'name': 'Artarad Zarinpal Payment Provider',

    'summary': 'Payment Provider: Zarinpal Implementation',

    'description': """Payment Provider: Zarinpal Implementation""",

    'author': "Artarad Team",
    
    'website': "https://www.artadoo.ir",

    'license': 'LGPL-3',

    'category': 'Accounting',
    
    'version': '1.0',
    
    'depends': ['account', 'payment',],

    'data': [
        'views/payment_provider_views.xml',
        'views/payment_zarinpal_templates.xml',
        'data/payment_provider_data.xml',
    ],

    'installable': True,
}