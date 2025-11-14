from odoo import models, fields, api,_
from odoo.exceptions import UserError


class ChequeChangeStateWizard(models.TransientModel):
    _name = 'change.cheque.state.wizard'
    _description = 'Cheque State Change'

    payment_ids = fields.Many2many('account.payment', string="Selected Records")
    new_cheque_state = fields.Many2one("artarad.pdc.st", required=True,)
    transaction_date = fields.Date(required=True)
    journal_id = fields.Many2one("account.journal",domain=[('type','in',('bank','post_dated_cheque'))], required=True,)
    debit_account = fields.Many2one("account.account",domain=[('deprecated', '=', False)])
    credit_account = fields.Many2one("account.account", domain=[('deprecated', '=', False)])

    def action_confirm(self):
        current_state = self.payment_ids.mapped("cheque_state")
        if len(current_state)>1:
            raise UserError(_("All of cheque must have one current state!"))
        for record in self.payment_ids:
           transition= self.env['artarad.pdc.st.chg.trans'].create({
               'old_cheque_state':record.cheque_state.id,
               'new_cheque_state':self.new_cheque_state.id,
                'transaction_date':self.transaction_date,
                'transaction_state':'draft',
                'payment_move':record.move_id.id,
                'payment':record.id,
                'journal_id':self.journal_id.id,
                'move_partner':record.partner_id.id,
                'debit_account':self.debit_account.id,
                'credit_account':self.credit_account.id,
            })
           transition.with_context(active_id=transition.id).change_state_to_posted()
        return {'type': 'ir.actions.act_window_close'}
