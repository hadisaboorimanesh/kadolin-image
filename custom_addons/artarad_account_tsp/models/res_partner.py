# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _


class artaradResPartner(models.Model):
    _inherit = "res.partner"

    tsp_default_type = fields.Selection([("1", "اول"),
                                         ("2", "دوم")], tracking=True, copy=False)
    tsp_default_pattern = fields.Selection([("1", "فروش"),
                                            ("2", "فروش ارزی"),
                                            ("7", "صادرات")], tracking=True, copy=False)
    national_number = fields.Char()