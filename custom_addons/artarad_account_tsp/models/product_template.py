# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _


class artaradProductTemplate(models.Model):
    _inherit = "product.template"


    tsp_code = fields.Char(string="Code")



class artaradProductProduct(models.Model):
    _inherit = "product.product"


    tsp_variant_code = fields.Char(string="Variant Code")