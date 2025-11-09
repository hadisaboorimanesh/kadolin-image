# -*- coding: utf-8 -*-
{
    "name": "AK Mobile First Login",
    "summary": "ورود/ثبت‌نام با شماره موبایل + OTP (اودو 18)",
    "version": "1.0.0",
    "author": "Artadoo Team",
    "website": "https://artadoo.ir",
    "license": "OEEL-1",
    "sequence": 100,
    "depends": ["website", "auth_signup","artarad_sms","website_sale"],
    "data": [
        "data/ir_config_parameter.xml",
        "views/templates.xml",
        "security/ir.model.access.csv",
    ],
    "assets": {},
    "application": False,
    "installable": True,
}
