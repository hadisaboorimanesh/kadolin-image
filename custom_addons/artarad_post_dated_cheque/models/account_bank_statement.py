# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _get_default_amls_matching_domain(self):
        domain = super(AccountBankStatementLine, self)._get_default_amls_matching_domain()
        # domain += [("move_id.payment_id.payment_method_line_id.payment_method_id.code", "!=", "cheque")]
        return domain

    def reconcile(self, lines_vals_list, to_check=False, allow_partial=False):
        super(AccountBankStatementLine, self).reconcile(lines_vals_list, to_check, allow_partial)

        move_line_ids = [item.get('id', False) for item in lines_vals_list]
        for payment in self.env['account.move.line'].browse(move_line_ids).mapped('payment_id'):
            if payment.cheque_state:
                last_transaction = self.env['artarad.pdc.st.chg.trans'].search([('payment','=',payment.id)], order="id desc", limit=1)
                new_transaction = self.env['artarad.pdc.st.chg.trans'].create({'payment': payment.id,
                                                                            'journal_id': last_transaction.journal_id.id,
                                                                            'transaction_date': fields.Date.today(),
                                                                            'old_cheque_state': payment.cheque_state.id,
                                                                            'new_cheque_state': self.env['artarad.pdc.st'].search([("is_receipted", "=", True)], limit=1).id})
                new_transaction.action_post()

    def button_undo_reconciliation(self):
        for line in self.line_ids.full_reconcile_id.reconciled_line_ids.filtered(lambda line: line.payment_id):
            if line.payment_id.cheque_state:
                line.payment_id.set_previuos_cheque_state()
        
        super(AccountBankStatementLine, self).button_undo_reconciliation()
