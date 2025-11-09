# -*- coding: utf-8 -*-
{
    'name': 'Artarad Auth Signup Mobile',
    
    'summary': 'Auth Signup Mobile',
    
    'description': """
    Signup page with mobile field and verification code
    """,
    
    'author': 'Artarad Team',
    
    'website': 'www.artarad.ir',
    
    'license': 'LGPL-3',
    
    'category': 'Website',
    
    'version': '1.0',

    'depends': [
        'auth_signup', 'artarad_sms',
    ],

    'assets': {
        'web.assets_frontend': [
            'artarad_auth_signup_mobile/static/**/*',
        ],
    },
    
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter_data.xml',
        'views/auth_signup_views.xml',
        'views/res_config_settings_views.xml',
    ],
}
