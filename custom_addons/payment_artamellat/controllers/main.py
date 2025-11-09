# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

import logging
import pprint

_logger = logging.getLogger(__name__)


class MellatController(http.Controller):
    _return_url = '/payment/mellat/return/'

    @http.route('/payment/mellat/return', type='http', auth='public', csrf=False, save_session=False)
    def mellat_return_from_checkout(self, **data):
        _logger.info("handling redirection from Mellat with data:\n%s", pprint.pformat(data))
        request.env['payment.transaction'].sudo()._handle_notification_data('mellat', data)
        return request.redirect('/payment/status')