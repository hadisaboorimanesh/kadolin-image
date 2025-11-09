from odoo import models, fields, api, exceptions, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auth_signup_with_mobile = fields.Boolean(string='Phone', default=True)


    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            auth_signup_with_mobile=get_param('auth_signup_with_mobile', 'False').lower() == 'true',
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('auth_signup_with_mobile', repr(self.auth_signup_with_mobile))
