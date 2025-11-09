# coding: utf-8
from odoo import api, fields, models, _


class ProviderMellat(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('mellat', 'Mellat')], ondelete={'mellat': 'cascade'})
    mellat_terminal_id = fields.Char('Terminal ID',  groups='base.group_user',help='شماره ترمینال')
    mellat_username = fields.Char('Username',  groups='base.group_user',help='نام کاربری')
    mellat_password = fields.Char('Password',  groups='base.group_user' ,help='رمز عبور')



    def _mellat_get_api_url(self):
        self.ensure_one()
        if self.state == 'enabled':
            return 'https://bpm.shaparak.ir/pgwchannel/startpay.mellat'
        else:
            return 'https://banktest.ir/gateway/pgw.bpm.bankmellat.ir/pgwchannel/startpay.mellat'