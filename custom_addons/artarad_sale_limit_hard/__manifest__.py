# -*- coding: utf-8 -*-
{
    "name": "Artarad Website Sale Hard Limit",
    "summary": "Hard server-side product quantity limit on website cart (all paths).",
    "version": "18.0.1.0.0",
    "license": "OEEL-1",
    "author": "Artarad",
    "depends": ["website_sale"],
    "data": [
        "views/views.xml",
        "views/templates.xml",
    ],
    "assets": {

    'web.assets_frontend': [
        'artarad_sale_limit_hard/static/src/js/limit_button_disable.js',
    ],

},
    "installable": True,
    "application": False,
}