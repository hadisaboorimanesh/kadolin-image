from odoo import models, fields, api, exceptions, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    mobile = fields.Char(related="partner_id.mobile", readonly=False)