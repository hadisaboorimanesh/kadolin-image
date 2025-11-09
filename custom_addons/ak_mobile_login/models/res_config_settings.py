# ak_mobile_login/models/res_config_settings.py
# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ak_sms_template_otp_id = fields.Many2one(
        "sms.template",
        string="OTP SMS Template",
        config_parameter="ak_mobile_login.sms_template_otp_id",
        help="قالب پیامکی که برای ارسال کد یکبارمصرف استفاده می‌شود.",
    )

    ak_sms_template_reset_id = fields.Many2one(
        "sms.template",
        string="Reset Password SMS Template",
        config_parameter="ak_mobile_login.sms_template_reset_id",
        help="قالب پیامکی که برای ارسال رمز جدید/لینک بازنشانی استفاده می‌شود.",
    )