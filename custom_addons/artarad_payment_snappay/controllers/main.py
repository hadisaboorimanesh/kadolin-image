# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class SnappPayController(http.Controller):
    _return_url = '/payment/snappay/return'
    # SnappPay ندارد: webhook
    # _webhook_url = '/payment/snappay/webhook'

    @http.route('/payment/snappay/return', type='http', auth='public', csrf=False, save_session=False)
    def snappay_return_from_checkout(self, **data):

        _logger.info("SnappPay return POST data:\n%s", pprint.pformat(data))

        # 1) خواندن پارامترها
        tx_id = data.get('transactionId')
        state = data.get('state')  # 'OK' or 'FAILED'
        amount = data.get('amount')  # ممکن است برای لاگ/مقایسه مفید باشد

        if not tx_id or not state:
            _logger.warning("SnappPay return missing required params (transactionId/state). Data: %s", data)
            return request.redirect('/payment/status')


        PaymentTransaction = request.env['payment.transaction'].sudo()

        tx_sudo = PaymentTransaction.search([
            ('provider_code', '=', 'snappay'),
            '|',('snappay_transaction_id', '=', tx_id),('reference', '=', tx_id),
        ], limit=1)
        if not tx_sudo:
            _logger.error("SnappPay: Transaction not found for transactionId=%s", tx_id)
            return request.redirect('/payment/status')

        if not getattr(tx_sudo, 'snappay_transaction_id', False):
            try:
                tx_sudo.write({'snappay_transaction_id': tx_id})
            except Exception:  # nosec - فقط برای اطمینان از عدم کرش
                _logger.exception("Failed to write snappay_transaction_id on tx %s", tx_sudo.id)

        try:
            if state == 'OK':
                tx_sudo._snappay_verify()
            else:
                tx_sudo._set_error(("Unknown payment state received: %s") % state)
                tx_sudo._set_canceled()
        except (ValidationError, UserError):
            _logger.exception("SnappPay verify/revert failed for tx %s with data %s", tx_sudo.id, data)

        return request.redirect('/payment/status')