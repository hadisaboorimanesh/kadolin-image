# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.http import request
from odoo.tools.translate import html_translate


class MegaMenuContent(models.Model):
    _name = 'mega.menu.content'
    _order = ''
    _description = "Mega Menu Content"

    website_menu_id = fields.Many2one("website.menu", string="website menu", readonly=True)
    sequence = fields.Integer(string="Sequence")
    url = fields.Char(string="Image/Button URL", required=False)
    image = fields.Image("Image", required=False)


