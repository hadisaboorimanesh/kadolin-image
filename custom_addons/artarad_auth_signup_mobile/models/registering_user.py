from odoo import models, fields, api, exceptions, _


class artaradRegisteringUser(models.Model):
    _name = "artarad.registering.user"
    _description = "Registering User"

    mobile = fields.Char()
    verif_code = fields.Char()