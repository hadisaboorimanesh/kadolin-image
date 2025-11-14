# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _


class artaradPDCStateChangeTransaction(models.Model):
    _name = "artarad.pdc.st.chg.trans"
    _description = "PDC State Change Transaction"
    _order = "id desc"

    # main fields
    active = fields.Boolean(default=True)

    name = fields.Char()
    old_cheque_state = fields.Many2one("artarad.pdc.st", ondelete="cascade", readonly=True, default=lambda self: self._set_old_cheque_state())
    new_cheque_state = fields.Many2one("artarad.pdc.st", required=True, ondelete='cascade')

    transaction_date = fields.Date(required=True)
    transaction_state = fields.Selection([("draft", "Draft"), ("posted", "Posted")], default="draft", readonly=True)

    debit_account = fields.Many2one("account.account", ondelete='cascade')
    credit_account = fields.Many2one("account.account", ondelete='cascade')

    description = fields.Char()

    journal_id = fields.Many2one("account.journal")
    move = fields.Many2one("account.move", string="Journal Entry", ondelete='cascade', readonly=True)
    move_partner = fields.Many2one("res.partner")

    # related fields
    cheque_date = fields.Date(string="Cheque Date", related='payment.cheque_date')
    payment_move = fields.Many2one(string="Payment Journal Entry", related='payment.move_id')
    new_cheque_state_is_spent = fields.Boolean(related='new_cheque_state.is_spent')
    company_id = fields.Many2one("res.company", related="old_cheque_state.company_id")

    cheque_number_description = fields.Char(related="payment.cheque_number_description", store=True)
    cheque_sayadi_number = fields.Char(related="payment.cheque_sayadi_number", store=True)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id")
    cheque_amount = fields.Monetary(related="payment.amount", store=True)
    cheque_bank_id = fields.Many2one("res.bank", related="payment.cheque_bank_id", store=True)


    # inverse fields
    payment = fields.Many2one("account.payment", string="Payment", readonly=True, ondelete='cascade',
                                default=lambda self: self._set_payment())

    # redundant fields
    payment_type = fields.Selection(readonly=True, related='payment.payment_type')

    # domain fields
    available_new_cheque_state_ids = fields.Many2many("artarad.pdc.st", compute="_compute_domain_fields")
    available_journal_ids = fields.Many2many("account.journal", compute="_compute_domain_fields")


    @api.depends("old_cheque_state")
    def _compute_domain_fields(self):
        for rec in self:
            rec.available_new_cheque_state_ids = self.env['artarad.pdc.st.chg'].search([('from_state', '=', rec.old_cheque_state.id)]).mapped("to_state")

            related_payment_id = self.env['account.payment'].browse(rec._context.get('active_id', False) or rec.payment.id)
            if rec.new_cheque_state and rec.new_cheque_state.is_returned:
                rec.available_journal_ids = self.env['account.journal'].search([('id', '=', related_payment_id.journal_id.id)])
            else:
                rec.available_journal_ids = self.env['account.journal'].search([('type', 'in', ['bank', 'cash', 'post_dated_cheque'])])

    @api.depends('name', 'company_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.name} ({rec.company_id.name})"

    @api.model
    def _set_payment(self):
        return self.env['account.payment'].browse(self._context.get('active_id'))

    @api.model
    def _set_old_cheque_state(self):
        payment = self.env['account.payment'].browse(self._context.get('active_id'))
        return payment.cheque_state

    @api.onchange("new_cheque_state")
    def _set_journal_and_partner_defaults_and_journal_domain(self):
        payment = self.env['account.payment'].browse(self._context.get('active_id', False) or self.payment.id)

        if self.new_cheque_state.is_returned:
            self.journal_id = payment.journal_id.id
            self.move_partner = payment.partner_id.id
        else:
            last_enteried_transaction = self.env['artarad.pdc.st.chg.trans'].search([('payment','=',payment.id), ('move', '!=', False)], order="id desc", limit=1)
            if last_enteried_transaction.id:
                self.journal_id = last_enteried_transaction.journal_id.id
                self.move_partner = (last_enteried_transaction.move.line_ids.mapped("partner_id").ids or [False])[0]
            else:
                self.journal_id = payment.journal_id.id
                self.move_partner = payment.partner_id.id

    @api.onchange("new_cheque_state")
    def _set_default_debit_and_credit_accounts(self):
        state_change = self.env['artarad.pdc.st.chg'].search([("from_state.id", "=", self.old_cheque_state.id), ("to_state.id", "=", self.new_cheque_state.id)])
        self.debit_account = state_change.default_debit_account.id
        self.credit_account = state_change.default_credit_account.id

    @api.model
    def create(self, vals):
        res = super(artaradPDCStateChangeTransaction, self).create(vals)
        res.name = res.old_cheque_state.name + " To " + res.new_cheque_state.name
        return res

    def write(self, vals):
        if 'active' not in vals and self.transaction_state == 'posted':
            raise exceptions.UserError(_("You can not modify a transaction that is already posted"))
        else:
            return super(artaradPDCStateChangeTransaction, self).write(vals)

    def unlink(self):
        if self.transaction_state == 'posted':
            raise exceptions.UserError(_("You can not delete a transaction that is already posted! Archive it instead."))
        else:
            super(artaradPDCStateChangeTransaction, self).unlink()

    def action_archive(self):
        if len(self) > 1:
            raise exceptions.UserError(_("You can only archive one transaction at a time!"))

        if self.env['artarad.pdc.st.chg.trans'].search([('payment', '=', self.payment.id)], order="id desc", limit=1).id != self.id:
            raise exceptions.UserError(_("You can only archive the last active transaction!"))

        res = super(artaradPDCStateChangeTransaction, self).action_archive()

        if self.move:
            # self.move.button_draft()
            self.move.button_cancel()

        self.payment.cheque_state = self.old_cheque_state.id
        return res

    def action_unarchive(self):
        raise exceptions.UserError(_("You can not unarchive a transaction!"))

    def get_reciept_account(self):
        if self.journal_id.type == 'post_dated_cheque':
            raise exceptions.UserError(_("You can not choose a cheque journal!"))

        debit=self.journal_id.inbound_payment_method_line_ids[0].payment_account_id
        last_transaction =  self.payment.cheque_state_change_transactions.filtered(lambda l:l.move and l.active).sorted('id',reverse=True)
        if last_transaction:
            credit = last_transaction[0].debit_account
        else:
            credit = self.payment.move_id.line_ids.filtered(lambda l: l.debit != 0).account_id
        return debit,credit


    def change_state_to_posted(self):
        otherTransactions = self.env['artarad.pdc.st.chg.trans'].search(
            [('payment', '=', self.payment.id), ('id', '!=', self.id)])
        for otherTransaction in otherTransactions:
            if otherTransaction.transaction_date < self.transaction_date and \
                    otherTransaction.transaction_state != "posted":
                raise exceptions.UserError(_("You must first confirm older transactions!"))

        if (self.debit_account.id == False and self.credit_account.id != False) or \
                (self.debit_account.id != False and self.credit_account.id == False):
            raise exceptions.UserError(_("Either both or none of accounts must be filled!"))

        if (self.debit_account.id and self.credit_account.id) or (self.new_cheque_state.is_payment_validator):
            if  self.debit_account.id==False and self.new_cheque_state.is_payment_validator:
                debit,credit = self.get_reciept_account()
                self.debit_account = debit
                self.credit_account = credit

            move_vals = {
                'date': self.transaction_date,
                'ref': self.payment.name,
                'company_id': self.payment.company_id.id,
                'journal_id': self.journal_id.id,
                'partner_id': self.move_partner.id,
                'payment_ids': False,
            }

            self.move = self.env['account.move'].create(move_vals)
            ####################################################
            move_line_vals = {
                'partner_id': self.move_partner.id,
                'move_id': self.move.id,
                'name': self.payment.name,
                'journal_id': self.journal_id.id,
                'currency_id': self.payment.currency_id.id,
            }
            ####################################################
            amount_in_company_currency = self.payment.currency_id._convert(self.payment.amount, self.company_id.currency_id, self.company_id, self.payment.date, False)
            ####################################################
            move_line_vals.update({'credit': amount_in_company_currency})
            move_line_vals.update({'debit': 0})
            move_line_vals.update({'amount_currency': -self.payment.amount})
            move_line_vals.update({'account_id': self.credit_account.id})
            credit_move_line = self.env['account.move.line'].with_context(check_move_validity=False).create(
                move_line_vals)
            ####################################################
            move_line_vals.update({'credit': 0})
            move_line_vals.update({'debit': amount_in_company_currency})
            move_line_vals.update({'amount_currency': self.payment.amount})
            move_line_vals.update({'account_id': self.debit_account.id})
            debit_move_line = self.env['account.move.line'].with_context(check_move_validity=False).create(
                move_line_vals)
            ####################################################
            self.move.action_post()
            ####################################################
            credit_move_line.payment_id = self.payment.id
            debit_move_line.payment_id = self.payment.id

        self.payment.cheque_state = self.new_cheque_state


        if self.payment.cheque_state.is_returned:
            for invoice in self.payment.reconciled_invoice_ids + self.payment.reconciled_bill_ids:
                for rpi in invoice.invoice_payments_widget['content']:
                    if rpi['account_payment_id'] == self.payment.id:
                        invoice.js_remove_outstanding_partial(rpi['partial_id'])
                invoice._compute_amount()


        if self.payment.cheque_state.is_payment_validator:
            self.payment.is_matched = True
            
            # 1 - update related invoices state
            for invoice in self.payment.reconciled_invoice_ids + self.payment.reconciled_bill_ids:
                invoice._compute_amount()

            # 2 - check if current cheque is spent in another payment
            if self.payment.spent_for:
                # 2.1 - update related invoices state of that payment, if all spent cheques in that payment are validated
                all_are_validated = True
                for payment in self.payment.spent_for.spending_cheques:
                    if not payment.cheque_state.is_payment_validator:
                        all_are_validated = False
                        break
                if all_are_validated:
                    self.payment.spent_for.is_matched = True
                    for invoice in self.payment.spent_for.reconciled_invoice_ids + self.payment.spent_for.reconciled_bill_ids:
                        invoice._compute_amount()


        if self.old_cheque_state.is_spent and self.new_cheque_state.is_payment_validator:
            # create final account move lines
            move_vals = {
                'date': self.transaction_date,
                'ref': self.payment.name,
                'company_id': self.payment.company_id.id,
                'journal_id': self.payment.spent_for.journal_id.id,
            }

            self.move = self.env['account.move'].create(move_vals)
            ####################################################
            move_line_vals = {
                'move_id': self.move.id,
                'debit': 0,
                'credit': 0,
                'amount_currency': 0.0,
                'name': self.payment.name,
                'journal_id': self.payment.spent_for.journal_id.id,
            }
            ####################################################
            move_line_vals.update({'account_id': self.payment.move_id.line_ids.filtered(lambda l: l.debit > 0).account_id.id})
            move_line_vals.update({'credit': self.payment.amount})
            move_line_vals.update({'debit': 0})
            move_line_vals.update({'partner_id': self.payment.move_id.line_ids.filtered(lambda l: l.debit > 0).partner_id.id})
            credit_move_line = self.env['account.move.line'].with_context(check_move_validity=False).create(move_line_vals)
            ####################################################
            move_line_vals.update({'account_id': self.payment.spent_for.move_id.line_ids.filtered(lambda l: l.credit > 0).account_id.id})
            move_line_vals.update({'credit': 0})
            move_line_vals.update({'debit': self.payment.amount})
            move_line_vals.update({'partner_id': self.payment.spent_for.move_id.line_ids.filtered(lambda l: l.credit > 0).partner_id.id})
            debit_move_line = self.env['account.move.line'].with_context(check_move_validity=False).create(move_line_vals)
            ####################################################
            self.move.action_post()

        self.transaction_state = "posted"