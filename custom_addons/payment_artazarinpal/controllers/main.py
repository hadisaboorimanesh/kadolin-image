# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

import logging
import pprint

_logger = logging.getLogger(__name__)


class ZarinpalController(http.Controller):
    _return_url = '/payment/zarinpal/return/'

    @http.route(
        _return_url, type='http', auth='public', methods=['GET', 'POST'], csrf=False,
        save_session=False
    )
    def zarinpal_return_from_checkout(self, **data):
        _logger.info("handling redirection from Zarinpal with data:\n%s", pprint.pformat(data))
        request.env['payment.transaction'].sudo()._handle_notification_data('zarinpal', data)
        return request.redirect('/payment/status')