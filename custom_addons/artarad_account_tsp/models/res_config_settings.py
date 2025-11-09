# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _


class artaradResCompany(models.Model):
    _inherit = "res.company"


    tsp_unique_id = fields.Char()
    tsp_private_key = fields.Text()
    tsp_include_description = fields.Boolean()
    tsp_include_uom = fields.Boolean()
    tsp_product_code_reference = fields.Selection([("product_template", "Product"), ("product_product", "Product Variant")], default="product_template")
    tsp_server_mode = fields.Selection([("primary", "Primary"), ("test", "Test")], default="primary")


class artaradResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"


    tsp_unique_id = fields.Char(related="company_id.tsp_unique_id", readonly=False)
    tsp_private_key = fields.Text(related="company_id.tsp_private_key", readonly=False)
    tsp_include_description = fields.Boolean(related="company_id.tsp_include_description", readonly=False)
    tsp_include_uom = fields.Boolean(related="company_id.tsp_include_uom", readonly=False)
    tsp_product_code_reference = fields.Selection(related="company_id.tsp_product_code_reference", readonly=False)
    tsp_server_mode = fields.Selection(related="company_id.tsp_server_mode", readonly=False)