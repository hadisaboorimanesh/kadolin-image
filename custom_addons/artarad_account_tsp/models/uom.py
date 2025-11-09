# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _


class Uom(models.Model):
    _inherit = 'uom.uom'


    tsp_code = fields.Char(string="TSP Code")