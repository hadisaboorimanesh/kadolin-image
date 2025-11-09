# -*- coding: utf-8 -*-
{
    'name': "Artarad WebSite Persian Calendar",

    'summary': """
       Convert gregorian calendar to jalaali in WebSite """,

    'description': """
        When your language is farsi in website, dates are in jalaali calendar.
    """,

    'author': "Artarad Team",
    
    'website': "https://www.artadoo.ir",

    'license': 'LGPL-3',

    'category': 'Website',
    
    'version': '1.0',

    'depends': ['base', 'website', 'website_blog', 'appointment', 'portal',],

    'data': [
        'views/appointment_templates_appointments.xml',
        'views/s_blog_posts.xml',
    ],

    'assets': {
        'web.assets_frontend': [
            ('after', 'appointment/static/src/js/appointment_select_appointment_slot.js', 'artarad_website_persian_calendar/static/src/js/appointment_select_appointment_slot.js'),
        ],
    },

    'installable': True,
    'auto_install': False,
}
