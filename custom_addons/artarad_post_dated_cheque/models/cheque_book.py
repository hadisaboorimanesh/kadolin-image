# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _


class artaradPDCBook(models.Model):
    _name = 'artarad.pdc.book'
    _description = 'PDC Book'

    bank = fields.Many2one('res.bank', string='Bank Name', required=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, domain=[('type', '=', 'bank')])
    sequence_numbers_prefix = fields.Char("Sequence Numbers Prefix", required=True)
    sequence_numbers_start = fields.Integer(string='Sequence Numbers Start', required=True)
    count_of_sheets = fields.Integer(string='Count of Sheets', required=True)
    sheets = fields.One2many('artarad.pdc.sheet', 'book', string="Sheets")
    company_id = fields.Many2one("res.company", related="journal_id.company_id")

    # domain fields
    available_journal_ids = fields.Many2many("account.journal", compute="_compute_available_journal_ids")

    
    @api.depends('bank', 'journal_id', 'sequence_numbers_prefix', 'sequence_numbers_start', 'company_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.bank.name} - {rec.journal_id.name} - {rec.sequence_numbers_prefix} - {rec.sequence_numbers_start} ({rec.company_id.name})"

    @api.depends('bank')
    def _compute_available_journal_ids(self):
        for rec in self:
            rec.available_journal_ids = self.env["account.journal"].search([('bank_id', '=', rec.bank.id)])

    @api.model
    def create(self, vals):
        res = super(artaradPDCBook, self).create(vals)

        for number in range(res.sequence_numbers_start,res.sequence_numbers_start + res.count_of_sheets):
            self.env['artarad.pdc.sheet'].create({
                'book': res.id,
                'number': number,
            })

        return res

    def unlink(self):
        for book in self:
            for sheet in book.sheets:
                if sheet.state != 'unused' and sheet.state != 'damaged':
                    raise exceptions.ValidationError(_('The book ' + book + ' has used sheet!'))
        return super(artaradPDCBook, self).unlink()




    
