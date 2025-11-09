# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _

import jdatetime


class artaradAccountMove(models.Model):
    _inherit = "account.move"
    
    def button_draft(self):
        for rec in self:
            # 1
            cheque_state_change_transaction = self.env['artarad.pdc.st.chg.trans'].search([('move', '=', rec.id)])
            if cheque_state_change_transaction:
                raise exceptions.UserError(_(f"You can not set to draft, because the entry is related to a state transaction of cheque: {cheque_state_change_transaction.payment.display_name}"))

            # 2
            if self.env['artarad.pdc.st.chg.trans'].search([('payment', '=', rec.origin_payment_id.id)]):
                raise exceptions.UserError(_(f"You can not set to draft, because the entry is related to a cheque that has state transactions: {rec.payment_id.display_name}"))

        return super(artaradAccountMove, self).button_draft()


class artaradAccountInvoice(models.Model):
    _inherit = "account.move"

    # overrided fields
    payment_state = fields.Selection(selection_add=[("partial_pdc", "Partial PDC"), ("pdc", "PDC"), ("paid",)],
                                     ondelete={"partial_pdc": lambda recs: recs.write({"payment_state": "partial"}), "pdc": lambda recs: recs.write({"payment_state": "paid"})})


    def get_cheques_data(self):
        has_inprogress_pdc = False
        has_inprogress_partial_pdc = False

        has_inprogress_cheque = False

        payments = self.env['account.payment'].browse([item['account_payment_id'] for item in self.invoice_payments_widget['content']] if self.invoice_payments_widget else [])
        for payment in payments:
            if payment.payment_method_id.code == 'cheque':
                if payment.payment_type == 'inbound':
                    if not payment.cheque_state.is_receipted:
                        has_inprogress_cheque = True
                        break

                elif payment.payment_type == 'outbound':
                    if payment.cheque_outbound_mode == 'draw':
                        if not payment.cheque_state.is_receipted:
                            has_inprogress_cheque = True
                            break
                    elif payment.cheque_outbound_mode == 'spend':
                        for spending_cheque in payment.spending_cheques:
                            if not spending_cheque.cheque_state.is_receipted:
                                has_inprogress_cheque = True
                                break


        if has_inprogress_cheque:
            if self.amount_residual:
                has_inprogress_partial_pdc = True
            else:
                has_inprogress_pdc = True

        return has_inprogress_pdc, has_inprogress_partial_pdc

    @api.depends('amount_residual', 'move_type', 'state', 'company_id')
    def _compute_payment_state(self):
        for move in self:
            has_inprogress_pdc, has_inprogress_partial_pdc = move.get_cheques_data()

            if has_inprogress_pdc:
                move.payment_state = 'pdc'
            elif has_inprogress_partial_pdc:
                move.payment_state = 'partial_pdc'
            else:
                super(artaradAccountInvoice, move)._compute_payment_state()

    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            company_id = m.company_id.id or self.env.company.id
            ########## overrided ##########
            """
            domain = [('company_id', '=', company_id), ('type', '=', journal_type)]
            """
            domain = [('company_id', '=', company_id), ('type', 'in', [journal_type, 'post_dated_cheque'])]
            ########## ######### ##########
            m.suitable_journal_ids = self.env['account.journal'].search(domain)


    def _compute_payments_widget_to_reconcile_info(self):
        for move in self:
            move.invoice_outstanding_credits_debits_widget = False
            move.invoice_has_outstanding = False

            ########## overrided ##########
            """
            if move.state != 'posted' \
                    or move.payment_state not in ('not_paid', 'partial') \
                    or not move.is_invoice(include_receipts=True):
                continue
            """
            if move.state != 'posted' \
                    or move.payment_state not in ('not_paid', 'partial', 'partial_pdc') \
                    or not move.is_invoice(include_receipts=True):
                continue
            ########## ######### ##########

            pay_term_lines = move.line_ids\
                .filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))

            domain = [
                ('account_id', 'in', pay_term_lines.account_id.ids),
                ('parent_state', '=', 'posted'),
                ('partner_id', '=', move.commercial_partner_id.id),
                ('reconciled', '=', False),
                '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
            ]
            
            ########## overrided ##########
            if move.is_inbound():
                domain += [('id', 'not in', self.env['artarad.pdc.st.chg.trans'].search([('new_cheque_state.is_returned', '=', True)]).mapped("payment.move_id.line_ids").ids)]
            elif move.state == 'out_invoice':
                domain += [('id', 'not in', self.env['artarad.pdc.st.chg.trans'].search([('old_cheque_state.is_spent', '=', True), ('new_cheque_state.code', '=', 'ICA')]).mapped("payment.move_id.line_ids").ids)]
            ########## ######### ##########

            payments_widget_vals = {'outstanding': True, 'content': [], 'move_id': move.id}

            if move.is_inbound():
                domain.append(('balance', '<', 0.0))
                payments_widget_vals['title'] = _('Outstanding credits')
            else:
                domain.append(('balance', '>', 0.0))
                payments_widget_vals['title'] = _('Outstanding debits')

            for line in self.env['account.move.line'].search(domain):

                if line.currency_id == move.currency_id:
                    # Same foreign currency.
                    amount = abs(line.amount_residual_currency)
                else:
                    # Different foreign currencies.
                    amount = line.company_currency_id._convert(
                        abs(line.amount_residual),
                        move.currency_id,
                        move.company_id,
                        line.date,
                    )

                if move.currency_id.is_zero(amount):
                    continue

                payments_widget_vals['content'].append({
                    'journal_name': line.ref or line.move_id.name,
                    'amount': amount,
                    'currency_id': move.currency_id.id,
                    'id': line.id,
                    'move_id': line.move_id.id,
                    'date': fields.Date.to_string(line.date),
                    'account_payment_id': line.payment_id.id,
                })

            if not payments_widget_vals['content']:
                continue

            move.invoice_outstanding_credits_debits_widget = payments_widget_vals
            move.invoice_has_outstanding = True