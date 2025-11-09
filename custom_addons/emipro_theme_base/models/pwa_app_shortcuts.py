# -*- coding: utf-8 -*-

from odoo import models, fields


class PWAAppShortcuts(models.Model):
    _name = "pwa.app.shortcut.ept"
    _description = 'PWA App Shortcut'

    name = fields.Char('Name', required=True)
    description = fields.Char('Description', required=True)
    url = fields.Char('URL', required=True)
    icon = fields.Image('Icon', required=True)
    website_id = fields.Many2one('website', string='Website', ondelete='cascade')
