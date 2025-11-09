# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _


class artaradAccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'


    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res['cheque'] = {'mode': 'multi', 'domain': [('type', '=', 'post_dated_cheque')]}
        return res


class artaradAccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"
    

    # Redifinition of fields

    payment_account_id = fields.Many2one(
        comodel_name='account.account',
        check_company=True,
        copy=False,
        ondelete='restrict',
        domain=lambda self: "[('deprecated', '=', False), "
                            "('account_type', 'not in', ('receivable', 'payable'))]"
    )