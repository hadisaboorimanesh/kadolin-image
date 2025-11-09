# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _


class artaradPDCStateChange(models.Model):
    _name = "artarad.pdc.st.chg"
    _description = "PDC State Change"

    # main fields
    from_state = fields.Many2one("artarad.pdc.st", required = True, ondelete='cascade')
    to_state = fields.Many2one("artarad.pdc.st", required = True, ondelete='cascade', domain = "[('id', '!=', from_state)]")
    default_debit_account = fields.Many2one("account.account", string = "Default Debit Account", ondelete='cascade')
    default_credit_account = fields.Many2one("account.account", string = "Default Credit Account", ondelete='cascade')
    company_id = fields.Many2one("res.company", related="from_state.company_id")

    
    @api.depends('from_state', 'to_state', 'company_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.from_state.name} - {rec.to_state.name} ({rec.company_id.name})"

    @api.model
    def create(self,vals):
        if (vals["default_debit_account"] == False and vals["default_credit_account"] != False) or \
            (vals["default_debit_account"] != False and vals["default_credit_account"] == False):
            raise exceptions.UserError(_("Either both or none of accounts must be filled!"))
        else:
            return super(artaradPDCStateChange, self).create(vals)

    def write(self,vals):
        if ("default_debit_account" in vals and "default_credit_account" not in vals and self.default_credit_account.id == False) or \
            ("default_debit_account" not in vals and "default_credit_account" in vals and self.default_debit_account.id == False):
            raise exceptions.UserError(_("Either both or none of accounts must be filled!"))
        else:
            return super(artaradPDCStateChange, self).write(vals)
		