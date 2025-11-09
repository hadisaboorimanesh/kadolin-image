# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _


class artaradPDCSheet(models.Model):
    _name = 'artarad.pdc.sheet'
    _description = 'PDC Sheet'

    number = fields.Integer(string="Number", required=True)
    book = fields.Many2one('artarad.pdc.book', ondelete='cascade')
    pay_to = fields.Many2one('res.partner', string='Pay to')
    date = fields.Date(string='Date')
    amount = fields.Float(string='Amount')
    payment = fields.Many2one('account.payment', string="Payment")
    state = fields.Selection([('unused','Unused'), ('drawn','Drawn'), ('cashed','Cashed'), ('damaged', 'Damaged')], string="State", default="unused")
    company_id = fields.Many2one("res.company", related="book.company_id")

    
    @api.depends('book', 'number', 'company_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.book.sequence_numbers_prefix} - {rec.number} ({rec.company_id.name})"

    def change_state_to_damaged(self):
        self.state = 'damaged'

    def set_as_used(self, payment):
        self.date = payment.cheque_date
        self.pay_to = payment.partner_id
        self.amount = payment.amount
        self.state = 'drawn'
        self.payment = payment.id

    def set_as_unused(self):
        self.date = \
        self.pay_to = \
        self.amount = \
        self.payment = \
        False
        self.state = 'unused'