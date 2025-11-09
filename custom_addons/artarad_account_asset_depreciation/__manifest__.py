# -*- coding: utf-8 -*-
{
    "name": "Artarad Account Asset Depreciation",

    "summary": """
        Account Asset Depreciation""",

    "description": """
        This module enables use of jalali calendar for assets depreciation.
    """,

    'author': "Artarad Team",
    
    'website': "https://www.artadoo.ir",

    'license': "LGPL-3",

    'category': "Accounting",
    
    'version': "1.0",

    "depends": ["account_asset",],

    "data": [
        'views/res_config_settings_views.xml',
    ],

    "installable": True,
    
    "auto_install": False,
}