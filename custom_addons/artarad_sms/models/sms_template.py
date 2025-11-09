# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _


class artaradSmsTemplate(models.Model):
    _inherit = "sms.template"


    model_id = fields.Many2one(
        'ir.model', string='Applies to', required=True,
        domain=[('transient', '=', False)],
        help="The type of document this template can be used with", ondelete='cascade')
    mobile_to = fields.Char("To (Numbers)", help="Comma-separated recipient mobile numbers (placeholders may be used here)")