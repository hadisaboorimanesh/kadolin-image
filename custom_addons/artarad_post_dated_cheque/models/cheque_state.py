# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _


class artaradPDCState(models.Model):
    _name = "artarad.pdc.st"
    _description = "PDC State"
    _rec_name = "name"

    # main fields
    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    is_payment_validator = fields.Boolean()
    is_returned = fields.Boolean()
    is_spent = fields.Boolean()
    is_spendable = fields.Boolean()
    company_id = fields.Many2one("res.company", required=True, readonly=True, default=lambda self: self.env.company)