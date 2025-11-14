# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _


class artaradAccountJournal(models.Model):
    _inherit = "account.journal"

    type = fields.Selection(selection_add=[("post_dated_cheque", "Post Dated Cheque")], ondelete={'post_dated_cheque': lambda recs: recs.write({'type': 'general'})})

    @api.depends('type')
    def _compute_default_account_type(self):
        default_account_id_types = {
            'post_dated_cheque': 'asset_cash',
            'bank': 'asset_cash',
            'cash': 'asset_cash',
            'sale': 'income',
            'purchase': 'expense'
        }

        for journal in self:
            if journal.type in default_account_id_types:
                journal.default_account_type = default_account_id_types[journal.type]
            else:
                journal.default_account_type = False

    # def _compute_available_payment_method_ids(self):
    #     super()._compute_available_payment_method_ids()
    #
    #     for rec in self:
    #         if rec.type in ['bank', 'cash', 'post_dated_cheque']:
    #             rec.available_payment_method_ids = [(4, self.env.ref('artarad_post_dated_cheque.account_payment_method_cheque_in').id), (4, self.env.ref('artarad_post_dated_cheque.account_payment_method_cheque_out').id)]