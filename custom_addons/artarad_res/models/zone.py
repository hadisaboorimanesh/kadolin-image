# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _


class artaradResZone(models.Model):
    _name = "artarad.res.zone"

    name = fields.Char()
    city_id = fields.Many2one('res.city')