# -*- coding: utf-8 -*-
{
    'name': "Artarad Res",

    'summary': "Artarad Res",

    'description':
    """
	Customization of res.partner, res.company and hr.employee\n
    res.partner: fields for national number, registeration number, economic number and authentication state.\n
    res.company: fields for configuring validity and uniqueness checks of national_number.
    hr.employee: field for first name.
    """,

    'author': "Artarad Team",

    'website': "https://www.artadoo.ir",

    'license': "LGPL-3",

    'category': "Base",

    'version': "1.0",

    'depends': ['base', 'base_address_extended', 'hr'],

    'data': [   
        'data/cities_data.xml',
        
        'views/res_partner_views.xml',
        'views/res_company_views.xml',
        'views/zone.xml',
        'security/ir.model.access.csv',
    ],

    'installable':True,
}
