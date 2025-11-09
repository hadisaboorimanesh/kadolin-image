from odoo import http, _
from odoo.addons.auth_signup.controllers.main import AuthSignupHome as Home
from odoo.exceptions import UserError
from odoo.http import request

import math
import random
import datetime


class AuthSignupHomeExt(Home):
    def get_auth_signup_qcontext(self):
        qcontext = super(AuthSignupHomeExt, self).get_auth_signup_qcontext()

        if request.env["ir.config_parameter"].sudo().get_param("auth_signup_with_mobile") == "True":
            qcontext['auth_signup_with_mobile'] = True
        else:
            qcontext['auth_signup_with_mobile'] = False
        return qcontext


    def _signup_with_values(self, token, values):
        if request.env["ir.config_parameter"].sudo().get_param("auth_signup_with_mobile") == "True":
            mobile = request.params["mobile"]
            verif_code = request.params["verif_code"]

            registering_user = request.env['artarad.registering.user'].sudo().search([('mobile', '=', mobile)])

            if request.env['res.partner'].sudo().search([('mobile', '=', mobile)]):
                raise UserError(_("Another user is already registered using this mobile."))
            if registering_user.write_date + datetime.timedelta(minutes=1) <= datetime.datetime.utcnow():
                raise UserError(_("Expired Verification code!"))
            if verif_code != registering_user.verif_code:
                raise UserError(_("Incorrect Verification code!"))

            registering_user.unlink()
            values["mobile"] = mobile

        return super(AuthSignupHomeExt, self)._signup_with_values(token, values)


class AuthSignupHTTP(http.Controller):

    @http.route('/authsignupsendsms', type='http', auth='none', methods=['POST'], csrf=False)
    def authsignupsendsms(self, *args, **post):
        code = str(math.floor(1000 + random.random() * 9000))
        # remove previous records for current mobile
        request.env['artarad.registering.user'].sudo().search([('mobile', '=', post['mobile'])]).unlink()
        # create new record
        request.env['artarad.registering.user'].sudo().create({'mobile': post['mobile'],
                                                                'verif_code': code})
        # send sms
        request.env['artarad.sms.provider.setting'].search([], order="sequence asc", limit=1).send_sms(post['mobile'], code)