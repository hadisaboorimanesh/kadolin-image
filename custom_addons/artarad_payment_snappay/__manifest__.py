{
    "name": "Artarad SnappPay Payment Provider",
    "summary": "Installment payment via SnappPay (redirect flow)",
    "version": "1.0.1",
    "category": "Accounting/Payment Providers",
    "depends": ["payment",'sale'],
    "data": [

        "views/payment_provider_views.xml",
        "views/payment_form_templates.xml",
        "views/payment_method_views.xml",
        "views/sale.xml",
        "views/website_templates.xml",
        "data/payment_provider_data.xml",

    ],
    "assets": {

    },
    "installable": True,
    "application": False,
}