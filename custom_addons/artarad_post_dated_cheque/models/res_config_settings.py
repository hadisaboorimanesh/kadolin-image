from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    finnotech_client_id = fields.Char(string="Finnotech Client ID", config_parameter="finnotech.client_id")
    national_id = fields.Char(string="Finnotech Client Secret", config_parameter="finnotech.national_id")
    # finnotech_subscription_id = fields.Char(string="Finnotech Subscription ID", config_parameter="finnotech.subscription_id")
