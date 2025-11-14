# -*- coding: utf-8 -*-
{
    'application': False,

    'name': "Artarad Post Dated Cheque",

    'summary': "Artarad Post Dated Cheque",

    'description':
        """
        ...
        """,

    'author': "Artarad Team",

    'website': "https://www.artadoo.ir",

    'license': "LGPL-3",

    'category': "Accounting",

    'version': "1.0",

    'depends': ['account', 'account_accountant', ],

    'data': [
        # 'report/cheque_print_reports.xml',
        # 'report/cheque_print_templates.xml',

        'views/account_journal_view.xml',
        'views/account_payment_view.xml',
        'views/account_invoice_view.xml',
        # 'views/account_journal_dashboard_view.xml',
        'views/cheque_book_view.xml',
        'views/cheque_sheet_view.xml',
        'views/cheque_initial_state_view.xml',
        'views/cheque_payment_view.xml',
        'views/cheque_state_change_transaction_view.xml',
        'views/cheque_state_change_view.xml',
        'views/cheque_state_view.xml',
        'views/res_config_settings_views.xml',
        'wizard/payment_ras_wizard_view.xml',
        'wizard/payment_action.xml',
        "wizard/cheque_wizard.xml",

        'data/defaultdata.xml',

        'security/ir.model.access.csv',
        'security/security.xml',

        'views/menus.xml',
    ],
}
