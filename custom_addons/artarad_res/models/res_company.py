from odoo import models, fields, api, exceptions, _


class artaradResCompany(models.Model):
    _inherit = 'res.company'
    
    # additional fields
    numbers_validity_check = fields.Boolean(string="National Number/ID Validity Check", default=False, help="Check validity of National Number/ID")
    numbers_uniqueness_check = fields.Boolean(string="National Number/ID Uniqueness Check", default=False, help="Check uniqueness of National Number/ID")