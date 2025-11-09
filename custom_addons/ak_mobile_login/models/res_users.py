# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import random, re
from datetime import timedelta

MOBILE_RE = re.compile(r'^(?:\+?98|0)?9\d{9}$')

def _normalize_mobile(m):
    if not m:
        return m
    m = re.sub(r'\D+', '', m)
    if m.startswith('989'):
        m = '0' + m[2:]
    if not m.startswith('0'):
        m = '0' + m
    return m

class ResUsers(models.Model):
    _inherit = 'res.users'

    login_mobile = fields.Char(string="Mobile (Login)", index=True)
    ak_last_otp = fields.Char(readonly=True)
    ak_otp_expire = fields.Datetime(readonly=True)

    _sql_constraints = [
        ('login_mobile_unique', 'unique (login_mobile)', 'این شماره موبایل قبلاً ثبت شده است.'),
    ]

    @api.constrains('login_mobile')
    def _check_mobile_format(self):
        for rec in self:
            if rec.login_mobile and not MOBILE_RE.match(rec.login_mobile):
                raise ValidationError(_('فرمت شماره موبایل صحیح نیست.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('login_mobile'):
                vals['login_mobile'] = _normalize_mobile(vals['login_mobile'])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('login_mobile'):
            vals['login_mobile'] = _normalize_mobile(vals['login_mobile'])
        return super().write(vals)

    def action_generate_otp(self, minutes=5, length=5):
        self.ensure_one()
        code = ''.join(random.choices('0123456789', k=length))
        self.write({
            'ak_last_otp': code,
            'ak_otp_expire': fields.Datetime.now() + timedelta(minutes=minutes),
        })
        return code

    def action_check_otp(self, code):
        self.ensure_one()
        if not code or not self.ak_last_otp or not self.ak_otp_expire:
            return False
        if fields.Datetime.now() > self.ak_otp_expire:
            return False
        return str(code) == str(self.ak_last_otp)

    @api.model
    def find_by_mobile(self, mobile):
        mobile = _normalize_mobile(mobile)
        return self.with_context(active_test=False).search(['|',('login_mobile', '=', mobile),('login', '=', mobile)], limit=1)

