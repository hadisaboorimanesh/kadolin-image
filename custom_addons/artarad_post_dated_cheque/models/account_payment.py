# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
from odoo.addons.account.models import account_payment as ap

import jdatetime
import requests
import json
from odoo.exceptions import UserError

class artaradAccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # overrided fields
    journal_id = fields.Many2one('account.journal', store=True, readonly=False,
    compute='_compute_journal_id',
    domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash', 'post_dated_cheque'))]", tracking=True)

    # additional fields
    cheque_outbound_mode = fields.Selection([('draw', 'Draw'), ('spend', 'Spend')], default='draw', string='Via')
    cheque_number = fields.Char(string="Serial")
    cheque_number_description = fields.Char(string="Class")
    cheque_sayadi_number = fields.Char(string="Sayadi Number")
    cheque_bank_id = fields.Many2one('res.bank', string='Bank')
    cheque_date = fields.Date(string="Cheque Date")
    cheque_state = fields.Many2one('artarad.pdc.st', string="Cheque State")
    cheque_book = fields.Many2one('artarad.pdc.book', string="Cheque Book")
    cheque_sheet = fields.Many2one('artarad.pdc.sheet', string="Cheque Sheet")
    spending_cheques = fields.Many2many('account.payment')

    # domain fields
    available_cheque_book_ids = fields.Many2many("artarad.pdc.book", compute="_compute_domain_fields")
    available_cheque_sheet_ids = fields.Many2many("artarad.pdc.sheet", compute="_compute_domain_fields")

    @api.depends("journal_id", "cheque_book")
    def _compute_domain_fields(self):
        for rec in self:
            rec.available_cheque_book_ids = self.env["artarad.pdc.book"].search([('journal_id', '=', rec.journal_id.id)])
            rec.available_cheque_sheet_ids = self.env["artarad.pdc.sheet"].search([('book', '=', rec.cheque_book.id), ('state', '=', 'unused')])

    # overrided methods
    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super(artaradAccountPaymentRegister,self)._create_payment_vals_from_wizard(batch_result)

        payment_vals['cheque_outbound_mode'] = self.cheque_outbound_mode
        payment_vals['cheque_number'] = self.cheque_number
        payment_vals['cheque_number_description'] = self.cheque_number_description
        payment_vals['cheque_sayadi_number'] = self.cheque_sayadi_number
        payment_vals['cheque_bank_id'] = self.cheque_bank_id.id
        payment_vals['cheque_date'] = self.cheque_date
        payment_vals['cheque_state'] = self.cheque_state.id
        payment_vals['cheque_book'] = self.cheque_book.id
        payment_vals['cheque_sheet'] = self.cheque_sheet.id
        payment_vals['spending_cheques'] = [(6, 0, self.spending_cheques.ids)]

        return payment_vals


    # additional methods

    @api.onchange('payment_type', 'journal_id', 'payment_method_line_id')
    def _set_pdc_initial_state(self):
        if self.payment_method_line_id.payment_method_id.code == 'cheque':
            if self.payment_type == 'outbound':
                self.cheque_state = self.env['artarad.pdc.init.st'].search([("type", "=", "IIP")]).state.id

                if self.journal_id.type == 'post_dated_cheque':
                    self.cheque_outbound_mode = 'spend'
                else:
                    self.cheque_outbound_mode = 'draw'

            elif self.payment_type == 'inbound':
                self.cheque_state = self.env['artarad.pdc.init.st'].search([("type", "=", "IIS")]).state.id
        else:
            self.cheque_state = \
            self.cheque_date = \
            self.cheque_book = \
            self.cheque_number = \
            self.cheque_number_description = \
            self.cheque_sayadi_number = \
            self.cheque_bank_id = \
            self.cheque_outbound_mode = \
            False

    @api.constrains('cheque_number')
    def _check_cheque_number_content(self):
        for rec in self:
            if rec.cheque_number and not rec.cheque_number.isdigit():
                raise exceptions.ValidationError(_("Cheque number field should only contain digits!"))

    @api.onchange('spending_cheques')
    def _compute_static_amount(self):
        if self.spending_cheques.ids:
            self.amount = 0
            self.amount = sum(self.spending_cheques.mapped('amount'))


class artaradAccountPayment(models.Model):
    _inherit = "account.payment"

    # there is 2 mode for outbound (or transfer outbound) types
    # 1: draw cheque sheet from own cheque books
    # 2: spend previously received cheques
    cheque_outbound_mode = fields.Selection([('draw', 'Draw'),
                                                ('spend', 'Spend')], default='draw', string='Via', tracking=True)

    # additional common fields between <<inbound>> and <<draw outbound>>
    cheque_number = fields.Char(string="Serial", copy=False, tracking=True)
    cheque_number_description = fields.Char(string="Class", copy=False, tracking=True)
    cheque_sayadi_number = fields.Char(string="Sayadi Number", copy=False, tracking=True)
    cheque_bank_id = fields.Many2one('res.bank', string='Bank')
    cheque_date = fields.Date(string="Cheque Date", tracking=True)
    cheque_state = fields.Many2one('artarad.pdc.st', string="Cheque State", copy=False, tracking=True, ondelete="restrict")

    cheque_state_change_transactions = fields.One2many('artarad.pdc.st.chg.trans','payment', string="State Change Transactions", copy=False)
    cheque_state_change_transactions_count = fields.Integer(string=" ", compute="_compute_cheque_state_change_transactions_count", readonly=True, copy=False)

    # additional exclusive fields for <<draw outbound>>
    cheque_book = fields.Many2one('artarad.pdc.book', string="Cheque Book", copy=False, tracking=True)
    cheque_sheet = fields.Many2one('artarad.pdc.sheet', string="Cheque Sheet", copy=False, tracking=True)

    # additional fields for <<spend outbound>>
    spending_cheques = fields.One2many('account.payment', 'spent_for', copy=False)

    # additional exclusive fields for <<inbound>>
    spent_for = fields.Many2one('account.payment', ondelete='set null', copy=False, tracking=True)

    # domain fields
    available_cheque_book_ids = fields.Many2many("artarad.pdc.book", compute="_compute_domain_fields")
    available_cheque_sheet_ids = fields.Many2many("artarad.pdc.sheet", compute="_compute_domain_fields")
    no_receipt = fields.Boolean(compute="_compute_no_receipt",store=True)
    no_receipt_for_out = fields.Boolean(compute="_compute_no_receipt",store=True)

    sayadi_cheque_status = fields.Char("Sayadi Cheque Status" ,readonly=1)  #  نتیجه استعلام
    cheque_type = fields.Selection([('paper','Paper'),('electronic','Electronic')])
    def _check_cheque_status(self):
        client_id = self.env['ir.config_parameter'].sudo().get_param('finnotech.client_id')
        national_id = self.env['ir.config_parameter'].sudo().get_param('finnotech.national_id')
        # subscription_id = self.env['ir.config_parameter'].sudo().get_param('finnotech.subscription_id')

        url = "https://api.finnotech.ir/dev/v2/oauth2/token"

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Basic QXJ0YXJhZDp1dTlacUR5aHM4bVdkdWYxUVBLSg=="
        }

        payload = {
            "grant_type": "client_credentials",
            "nid": "0901296643",
            "scopes": "credit:sayad-serial-inquiry:get"
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))



        if response.status_code != 200:
            raise UserError("خطا در گرفتن توکن از فینوتک")

        access_token = response.json()['result']['value']

        for payment in self:
            if not payment.cheque_sayadi_number:
                continue

            url = f"https://api.finnotech.ir/credit/v2/clients/{client_id}/sayadSerialInquiry"
            params = {
                "trackId": "",
                "sayadId": payment.cheque_sayadi_number
            }

            headers = {
                "Authorization": f"Bearer {access_token}"
            }

            response = requests.get(url, headers=headers, params=params)

            # بررسی و چاپ نتیجه
            if response.status_code == 200:
                print("✅ پاسخ موفق:")
                print(response.json())
            else:
                print(f"❌ خطا در درخواست: {response.status_code}")
                print(response.text)

            # if response.status_code == 200:
            #     result = response.json()
            #     payment.cheque_status = result.get('status', 'No status')
            # else:
            #     payment.cheque_status = f"خطا {response.status_code}"

    @api.depends("cheque_state_change_transactions","cheque_state")
    def _compute_no_receipt(self):
        for rec in self:
            if rec.payment_type == 'inbound':
                last = rec.cheque_state_change_transactions.filtered(lambda l: l.new_cheque_state.is_payment_validator or l.new_cheque_state.is_spent ).sorted("id")
                if last and jdatetime.datetime.fromgregorian(date=rec.date).strftime(
                        '%Y') == jdatetime.datetime.fromgregorian(date=last[0].transaction_date).strftime('%Y'):
                    rec.no_receipt = False
                else:
                    rec.no_receipt = True
                if rec.spent_for and jdatetime.datetime.fromgregorian(date=rec.date).strftime(
                        '%Y') == jdatetime.datetime.fromgregorian(date=rec.spent_for.date).strftime('%Y'):
                    rec.no_receipt = False
            if rec.cheque_sheet and not rec.cheque_state_change_transactions_count:
                rec.no_receipt_for_out = True
    @api.depends("journal_id", "cheque_book")
    def _compute_domain_fields(self):
        for rec in self:
            rec.available_cheque_book_ids = self.env["artarad.pdc.book"].search([('journal_id', '=', rec.journal_id.id)])
            rec.available_cheque_sheet_ids = self.env["artarad.pdc.sheet"].search([('book', '=', rec.cheque_book.id), ('state', '=', 'unused')])

    #overrided methods
    def _get_default_journal(self):
        ''' Retrieve the default journal for the account.payment.
        /!\ This method will not override the method in 'account.move' because the ORM
        doesn't allow overriding methods using _inherits. Then, this method will be called
        manually in 'create' and 'new'.
        :return: An account.journal record.
        '''
        return self.env['account.move']._search_default_journal(('bank', 'cash', 'post_dated_cheque'))


    @api.depends('move_id.line_ids.amount_residual', 'move_id.line_ids.amount_residual_currency', 'move_id.line_ids.account_id')
    def _compute_reconciliation_status(self):
        super(artaradAccountPayment,self)._compute_reconciliation_status()

        for pay in self:
            if pay.cheque_state.is_payment_validator:
                pay.is_matched = True


    def _register_hook(self):
        def _synchronize_from_moves(self, changed_fields):
            ''' Update the account.payment regarding its related account.move.
            Also, check both models are still consistent.
            :param changed_fields: A set containing all modified fields on account.move.
            '''
            if self._context.get('skip_account_move_synchronization'):
                return

            for pay in self.with_context(skip_account_move_synchronization=True):

                # After the migration to 14.0, the journal entry could be shared between the account.payment and the
                # account.bank.statement.line. In that case, the synchronization will only be made with the statement line.
                if pay.move_id.statement_line_id:
                    continue

                move = pay.move_id
                move_vals_to_write = {}
                payment_vals_to_write = {}

                if 'journal_id' in changed_fields:
                    if pay.journal_id.type not in ('bank', 'cash', 'post_dated_cheque'):
                        raise exceptions.UserError(_("A payment must always belongs to a bank or cash journal."))

                if 'line_ids' in changed_fields:
                    all_lines = move.line_ids
                    liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

                    if len(liquidity_lines) != 1:
                        raise exceptions.UserError(_(
                            "Journal Entry %s is not valid. In order to proceed, the journal items must "
                            "include one and only one outstanding payments/receipts account.",
                            move.display_name,
                        ))

                    if len(counterpart_lines) != 1:
                        raise exceptions.UserError(_(
                            "Journal Entry %s is not valid. In order to proceed, the journal items must "
                            "include one and only one receivable/payable account (with an exception of "
                            "internal transfers).",
                            move.display_name,
                        ))

                    if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                        raise exceptions.UserError(_(
                            "Journal Entry %s is not valid. In order to proceed, the journal items must "
                            "share the same currency.",
                            move.display_name,
                        ))

                    if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
                        raise exceptions.UserError(_(
                            "Journal Entry %s is not valid. In order to proceed, the journal items must "
                            "share the same partner.",
                            move.display_name,
                        ))

                    if counterpart_lines.account_id.account_type == 'asset_receivable':
                        partner_type = 'customer'
                    else:
                        partner_type = 'supplier'

                    liquidity_amount = liquidity_lines.amount_currency

                    move_vals_to_write.update({
                        'currency_id': liquidity_lines.currency_id.id,
                        'partner_id': liquidity_lines.partner_id.id,
                    })
                    payment_vals_to_write.update({
                        'amount': abs(liquidity_amount),
                        'partner_type': partner_type,
                        'currency_id': liquidity_lines.currency_id.id,
                        'destination_account_id': counterpart_lines.account_id.id,
                        'partner_id': liquidity_lines.partner_id.id,
                    })
                    if liquidity_amount > 0.0:
                        payment_vals_to_write.update({'payment_type': 'inbound'})
                    elif liquidity_amount < 0.0:
                        payment_vals_to_write.update({'payment_type': 'outbound'})

                move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
                pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))

        ap.AccountPayment._synchronize_from_moves = _synchronize_from_moves

    def action_post(self):
        super(artaradAccountPayment, self).action_post()
        if self.spending_cheques.ids:
            credit_journal_item_name = _(f'Spending of cheques: ')
            for cheque in self.spending_cheques:
                # 1
                new_transaction = self.env['artarad.pdc.st.chg.trans'].create({'payment': cheque.id,
                                                                            'transaction_date': fields.Date.today(),
                                                                            'journal_id': self.journal_id.id,
                                                                            'move_partner': self.move_id.partner_id.id,
                                                                            'old_cheque_state': cheque.cheque_state.id,
                                                                            'new_cheque_state': self.env['artarad.pdc.st'].search([("is_spent", "=", True)], limit=1).id})
                new_transaction.change_state_to_posted()

                # 2
                credit_journal_item_name += f'{cheque.cheque_number + ("(" + cheque.cheque_number_description + ")" if cheque.cheque_number_description else "")} | {jdatetime.datetime.fromgregorian(date=cheque.cheque_date).strftime("%Y/%m/%d")} - '

            credit_journal_item_name = credit_journal_item_name[:-3]
            self.move_id.line_ids.filtered(lambda l: l.credit > 0).name = credit_journal_item_name


    def action_draft(self):
        if self.cheque_outbound_mode == 'spend' and any([not sc.cheque_state.is_spent for sc in self.spending_cheques]):
            raise exceptions.UserError(_("One or more spending cheques are receipted!"))
        super(artaradAccountPayment, self).action_draft()
        self.spending_cheques.set_previuos_cheque_state()

    def action_cancel(self):
        super(artaradAccountPayment, self).action_cancel()
        
        for record in self:
            if record.payment_method_line_id.payment_method_id.code == 'cheque':

                if record.payment_type == 'outbound':
                    record.cheque_state = self.env['artarad.pdc.init.st'].search([("type", "=", "IIP")]).state.id
                elif record.payment_type == 'inbound':
                    record.cheque_state = self.env['artarad.pdc.init.st'].search([("type", "=", "IIS")]).state.id

                record.cheque_date = False
                record.spent_for = False
                record.spending_cheques = [(5,)]

                if record.cheque_sheet:
                    record.cheque_sheet.set_as_unused()
                    record.cheque_book = \
                    record.cheque_sheet = False


    @api.model
    def create(self,vals):
        payment_method = self.env['account.payment.method.line'].browse(vals.get('payment_method_line_id', False))
        if payment_method.code == 'cheque':
            journal = self.env['account.journal'].browse(vals['journal_id'])
            if journal.default_account_id.id == False:
                raise exceptions.UserError(_("Default Debit & Credit Accounts of PDC journals are not set!"))

        rec = super(artaradAccountPayment, self).create(vals)

        if rec.cheque_sheet:
            rec.cheque_sheet.set_as_used(rec)

        return rec

    def write(self, vals):
        if len(self) > 1 and 'cheque_state' in vals:
            # bussiness for state change through list view (multi selected)
            self.register_multi_transaction(vals['cheque_state'])
        else:
            self.update_cheque_fields(vals)

    def unlink(self):
        removingChequeSheets = self.env['artarad.pdc.sheet']
        for record in self:
            if record.cheque_sheet:
                removingChequeSheets += record.cheque_sheet

        result = super(artaradAccountPayment, self).unlink()

        if result:
            for sheet in removingChequeSheets:
                sheet.set_as_unused()
            
        return result

    #additional methods

    @api.onchange('is_internal_transfer', 'payment_type', 'journal_id', 'payment_method_line_id')
    def _set_pdc_initial_state(self):
        if self.payment_method_line_id.payment_method_id.code == 'cheque':
            if self.payment_type == 'outbound':
                self.cheque_state = self.env['artarad.pdc.init.st'].search([("type", "=", "IIP")]).state.id

                if self.journal_id.type == 'post_dated_cheque':
                    self.cheque_outbound_mode = 'spend'
                else:
                    self.cheque_outbound_mode = 'draw'

            elif self.payment_type == 'inbound':
                self.cheque_state = self.env['artarad.pdc.init.st'].search([("type", "=", "IIS")]).state.id
        else:
            self.cheque_state = \
            self.cheque_date = \
            self.cheque_book = \
            self.cheque_number = \
            self.cheque_number_description = \
            self.cheque_sayadi_number = \
            self.cheque_bank_id = \
            self.cheque_outbound_mode = \
            False

    @api.constrains('cheque_number')
    def _check_cheque_number_content(self):
        for rec in self:
            if rec.cheque_number and not rec.cheque_number.isdigit():
                raise exceptions.ValidationError(_("Cheque number field should only contain digits!"))

    @api.onchange('amount', 'cheque_number')
    def _duplicate_warning(self):
        if self.amount and self.cheque_number:
            duplicate_cheque = self.env['account.payment'].search([('amount', '=', self.amount), ('cheque_number', '=', self.cheque_number), ('state', '!=', 'cancel')], limit=1)
            if duplicate_cheque:
                return {'warning': {'title': _('Duplicate Cheque!'),
                                    'message' : _(f'A cheque with this amount and number already exists for {duplicate_cheque.partner_id.name}({duplicate_cheque.name} | {duplicate_cheque.cheque_number + ("(" + duplicate_cheque.cheque_number_description + ")" if duplicate_cheque.cheque_number_description else "")})!')}}

    @api.onchange('spending_cheques')
    def _compute_static_amount(self):
        if self.spending_cheques:
            self.amount = 0
            self.amount = sum(self.spending_cheques.mapped('amount'))

    def _compute_cheque_state_change_transactions_count(self):
        for payment in self:
            transactions = self.env['artarad.pdc.st.chg.trans'].search([("payment.id", "=", payment.id)])
            payment.cheque_state_change_transactions_count = len(transactions)

    def set_previuos_cheque_state(self):
        for payment in self:
            if payment.payment_method_line_id.payment_method_id.code == 'cheque':
                
                last_transaction = self.env['artarad.pdc.st.chg.trans'].search([('payment','=',payment.id)], order="id desc", limit=1)
                if last_transaction:
                    new_transaction = self.env['artarad.pdc.st.chg.trans'].create({'payment': payment.id,
                                                                                'journal_id': last_transaction.journal_id.id,
                                                                                'transaction_date': fields.Date.today(),
                                                                                'old_cheque_state': last_transaction.new_cheque_state.id,
                                                                                'new_cheque_state': last_transaction.old_cheque_state.id})
                    new_transaction.change_state_to_posted()
                else:
                    if payment.payment_type == 'outbound':
                        payment.cheque_state = self.env['artarad.pdc.init.st'].search([("type", "=", "IIP")]).state.id
                    elif payment.payment_type == 'inbound':
                        payment.cheque_state = self.env['artarad.pdc.init.st'].search([("type", "=", "IIS")]).state.id


    def register_multi_transaction(self, new_state_id):
        unreceiptable_cheques = {'undefined_state_change': [], 'already_in_state': []}
        for payment in self:
            if payment.cheque_state.id != new_state_id:
                change = self.env['artarad.pdc.st.chg'].search([('from_state','=', payment.cheque_state.id),
                                                                        ('to_state','=', new_state_id)])
                if change:
                    previous_transaction = self.env['artarad.pdc.st.chg.trans'].search([('payment','=', payment.id), ('transaction_state','=', 'posted')], order="id desc", limit=1)
                    transaction = self.env['artarad.pdc.st.chg.trans'].create({'payment': payment.id,
                                                                                'journal_id': previous_transaction.journal_id.id,
                                                                                'old_cheque_state': payment.cheque_state.id,
                                                                                'new_cheque_state': new_state_id,
                                                                                'transaction_date': payment.cheque_date})
                    
                    transaction._set_journal_and_partner_defaults_and_journal_domain()
                    transaction._set_default_debit_and_credit_accounts()
                    transaction.change_state_to_posted()
                else:
                    unreceiptable_cheques['undefined_state_change'].append(payment)
            else:
                unreceiptable_cheques['already_in_state'].append(payment)

        message = ""
        if len(unreceiptable_cheques['already_in_state']):
            message += _("The following cheques are already in the selected state:\n")
            for cheque in unreceiptable_cheques['already_in_state']:
                message += "- " + cheque.name + "\n"
        if len(unreceiptable_cheques['undefined_state_change']):
            message += _("The following cheques could not be in the selected state bacause of undefined state change:\n")
            for cheque in unreceiptable_cheques['undefined_state_change']:
                message += "- " + cheque.name + "\n"

        if len(message):
            raise exceptions.UserError(message)


    def update_cheque_fields(self, vals):
        for payment in self:
            old_sheet = payment.cheque_sheet
            if 'payment_method_line_id' in vals:
                payment_method_line = self.env['account.payment.method.line'].browse(vals.get('payment_method_line_id',False) or payment.payment_method_line_id.id)

                if payment_method_line.payment_method_id.code != 'cheque':
                    vals['cheque_sheet'] = False
                    vals['spent_for'] = False
                    vals['spending_cheques'] = [(5,)]
                else:
                    journal = self.env['account.journal'].browse(vals.get('journal_id',False) or payment.journal_id.id)
                    if journal.default_account_id.id == False:
                        raise exceptions.UserError(_("Default Debit & Credit Accounts of PDC journals are not set!"))

            super(artaradAccountPayment, payment).write(vals)

            new_sheet = payment.cheque_sheet
            if not old_sheet and new_sheet:
                new_sheet.set_as_used(payment)
            elif old_sheet and not new_sheet:
                old_sheet.set_as_unused()
            elif old_sheet and new_sheet and old_sheet != new_sheet:
                old_sheet.set_as_unused()
                new_sheet.set_as_used(payment)
    def action_change_cheque_state_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Change Cheque State'),
            'res_model': 'change.cheque.state.wizard',
            'view_mode': 'form',
            'context': {
                'default_payment_ids': [(6, 0, self.ids)],
            },
            'target': 'new',
        }
