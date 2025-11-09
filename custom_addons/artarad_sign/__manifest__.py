# -*- coding: utf-8 -*-
{
    'installable':True,

    'name': "Artarad Sign",

    'summary': "Artarad Sign",

    'description':
    """
	Correction of putting persian letters on PDFs.
    """,

    'author': "Artarad Team",

    'license': "",

    'website': "https://www.artadoo.ir",

    'category': "Sales/Sign",

    'version': "1.0",

    'depends': ['base', 'sign',],

    'external_dependencies': {
        'python': ['rtl', 'pybidi'],
    },

    'data': [
        'data/config_parameter.xml',
    ],
}
