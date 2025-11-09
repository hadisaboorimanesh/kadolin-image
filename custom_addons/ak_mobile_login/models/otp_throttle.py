# models/otp_throttle.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AkOtpThrottle(models.Model):
    _name = 'ak.otp.throttle'
    _description = 'OTP Send Throttle'
    _rec_name = 'mobile'

    mobile = fields.Char(required=True, index=True)
    last_sent = fields.Datetime(required=True, index=True)

    _sql_constraints = [
        ('mobile_unique', 'unique(mobile)', 'Throttle row already exists for this mobile.'),
    ]