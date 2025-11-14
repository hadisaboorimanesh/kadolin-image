# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.http import request

class Website(models.Model):
    _inherit = "website"

    enable_product_limits = fields.Boolean()