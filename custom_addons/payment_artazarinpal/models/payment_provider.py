# coding: utf-8
from odoo import api, fields, models, _


class ProviderZarinpal(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('zarinpal', 'Zarinpal')], ondelete={'zarinpal': 'cascade'})
    zarinpal_merchant_id = fields.Char('Merchant ID', required_if_provider='zarinpal', groups='base.group_user')

    def _zarinpal_get_api_url(self):
        self.ensure_one()
        if self.state == 'enabled':
            return 'https://www.zarinpal.com/pg/StartPay/'
        else:
            return ''