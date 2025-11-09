# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    account_asset_depreciation_calendar_type = fields.Selection([("jalaali", "Jalaali"), ("gregorian", "Gregorian")], default="jalaali", required=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_asset_depreciation_calendar_type = fields.Selection(related='company_id.account_asset_depreciation_calendar_type', readonly=False)