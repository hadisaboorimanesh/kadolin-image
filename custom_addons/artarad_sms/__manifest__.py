# -*- coding: utf-8 -*-
{
    'name': "Artarad SMS",

    'summary': """
        Enable using of iranian sms providers
        """,

    'description': """
       Send SMS with iranian sms providers
       """,

    'author': "Artarad Team",

    'website': "http://www.artarad.ir",

    'category': 'Hidden/Tools',

    'version': '17.1.1',

    'depends': ['base', 'sms', 'phone_validation', ],

    'external_dependencies': {
        'python': ['suds', ],
    },

    'data': [
        'security/ir.model.access.csv',
        'views/sms_provider_setting_views.xml',
        'views/sms_template_views.xml',
        'views/menus.xml',
    ],


}
