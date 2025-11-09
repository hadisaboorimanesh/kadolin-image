{
    "name": "Artarad Base Accounting",
    "version": "1.0",
    "category": "Accounting/Localizations/Account Charts",
    "summary": """Iran accounting chart and localization.""",
    "author": "Artadoo Team",
    "license": "AGPL-3",
    "website": "https://www.artadoo.ir",
    "depends": ["account", "sale", "purchase", ],
    "data": [
        'security/ir.model.access.csv',
        'security/security.xml',
        "data/res_currency_data.xml",
        "data/res.bank.csv",
        "views/menus.xml",
    ],
}
