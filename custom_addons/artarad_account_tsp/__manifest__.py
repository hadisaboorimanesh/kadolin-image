{
    'name': "Artarad Account TSP",
    
    'summary':'Account TSP',
    
    'description':
    """
	A module for sending invoices to tsp service of Iran tax organization.
    """,
    
    'author': "Artarad Team",

    'license': "LGPL-3",

    'website': "https://www.artadoo.ir",

    'category': "Accounting",

    'version': "1.0",
    
    'depends': ['base', 'product', 'account'],

    'external_dependencies': {
        'python': ['pycryptodomex', ],
    },

    'data': [
        'data/default_data.xml',
        'views/product_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/account_invoice_views.xml',
        'views/uom_views.xml',
    ],
    
    'installable': True,
}