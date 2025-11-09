# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _


class artaradPDCInitialState(models.Model):
    _name = "artarad.pdc.init.st"
    _description = "PDC Initial State"
    _rec_name = "type"

    # main fields
    type = fields.Selection([('IIS', 'Initial in Sale'), ('IIP', 'Initial in Purchase')], string = "Type", required = True)
    state = fields.Many2one("artarad.pdc.st", string = "State", required = True, ondelete='cascade')
    company_id = fields.Many2one("res.company", related="state.company_id")

    
    @api.depends('type', 'company_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.type} ({rec.company_id.name})"

    @api.model
    def create(self, vals):
        if self.env['artarad.pdc.init.st'].search([('type', '=', vals['type'])]).filtered(lambda pis: pis.company_id.id == self.env.company.id):
           raise exceptions.ValidationError(_('Each company should not have more than one initial state for sale or purchase'))
        return super(artaradPDCInitialState, self).create(vals)