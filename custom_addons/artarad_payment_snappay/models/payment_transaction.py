# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from werkzeug import urls
from werkzeug import urls as wkurls

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)
import uuid


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # ====== SnappPay specific storage ======
    snappay_payment_token = fields.Char(readonly=True)
    snappay_transaction_id = fields.Char(readonly=True)

    def _get_specific_rendering_values(self, processing_values):

        rendering_values = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'snappay':
            return rendering_values

        provider = self.provider_id
        base_url = provider.get_base_url()
        return_url = urls.url_join(base_url, provider.snappay_return_url or '/payment/snappay/return')
        cart_item = []
        for line in self.sale_order_ids.order_line.filtered(lambda l:l.product_id.type=='consu' and l.product_uom_qty>0):
            cart_item.append(
                {
                    "id": line.id,
                    "name": line.product_id.name,
                    "category": line.product_id.categ_id.name,
                    "count": line.product_uom_qty,
                    'commissionType': 100,
                    "amount": 10*int(round(line.price_unit, 0)),

                })

        delivery_amount = sum(self.sale_order_ids.order_line.filtered(lambda l:l.is_delivery).mapped("price_total"))
        t_amount =sum(self.sale_order_ids.mapped("amount_total"))
        line_amount= sum(self.sale_order_ids.order_line.filtered(lambda l:l.product_id.type=='consu').mapped("price_total"))
        disc_amount =abs(sum(self.sale_order_ids.order_line.filtered(lambda l:l.price_unit < 0).mapped("price_total")))
        cart_list = [{
            "cartId": self.sale_order_ids[0].id,
            "cartItems": cart_item,
            "isShipmentIncluded": True,
            "shippingAmount": 10*int(delivery_amount),
            "taxAmount": 0,
            "totalAmount": 10*int(round(t_amount, 0)+disc_amount),
            'isTaxIncluded': True,
        }]

        transaction_id = self.reference
        # transaction_id = f"{self.reference}-{uuid.uuid4().hex[:8]}"
        mobile = (self.partner_id.phone or self.partner_id.mobile or "").strip()
        if mobile:
            if mobile.startswith('0'):
                mobile = '+98' + mobile[1:]
            elif not mobile.startswith('+98'):
                mobile = '+98' + mobile
        else:
            _logger.warning("SnappPay: partner %s has no mobile, using default test number", self.partner_id)
            mobile = '+989000000000'
        mobile = mobile.replace(" ","")
        try:
            payment_token, payment_page_url = provider.snappay_get_payment_token(
                amount=10*int(round(t_amount, 0)),
                discount_amount=10* disc_amount,
                cart_list=cart_list,
                return_url=return_url,
                transaction_id=transaction_id,
                payment_method_type="INSTALLMENT",
                mobile=mobile.replace(" ",""),
            )
        except UserError as e:
            raise UserError(_("SnappPay token request failed: %s") % e)

        if not payment_page_url:
            raise UserError(_("SnappPay: No payment page URL returned."))

        self.write({
            'snappay_payment_token': payment_token or False,
            'provider_reference': payment_token or False,
        })

        u = wkurls.url_parse(payment_page_url)  # werkzeug.urls.Url
        api_base = f"{u.scheme}://{u.netloc}{u.path}"
        qdict = wkurls.url_decode(u.query)  # MultiDict

        # تبدیل MultiDict به dict ساده (آخرین مقدار هر کلید)
        url_params = {k: qdict.getlist(k)[-1] for k in qdict.keys()}

        return {
            **rendering_values,
            'api_base': api_base,
            'url_params': url_params,
        }

    # ====== Finding the transaction on return/webhook ======
    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """
        Override of `payment`:
        SnappPay پس از بازگشت، فیلدهای `transactionId`, `state`, `amount` را می‌فرستد.
        بر اساس transactionId (همان reference ما) تراکنش را پیدا می‌کنیم.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'snappay' or len(tx) == 1:
            return tx

        reference = notification_data.get('transactionId')
        if not reference:
            raise ValidationError(
                "SnappPay: " + _("Received data with missing transactionId.")
            )

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'snappay')], limit=1)
        if not tx:
            raise ValidationError(
                "SnappPay: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    # ====== Processing notification ======
    def _process_notification_data(self, notification_data):
        """
        Override of `payment`:
        بر اساس state: OK/FAILED → verify یا revert را صدا می‌زنیم.
        در صورت OK و verify موفق → _set_done()
        در غیر این صورت → _set_error() یا _set_canceled()
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'snappay':
            return

        provider = self.provider_id

        state = (notification_data.get('state') or '').upper()
        returned_amount = notification_data.get('amount')
        try:
            returned_amount = int(returned_amount) if returned_amount is not None else None
        except Exception:
            returned_amount = None

        # در صورت امکان، تطابق مبلغ
        if returned_amount is not None and int(round(self.amount, 0)) != returned_amount:
            _logger.warning(
                "SnappPay: Returned amount (%s) mismatches tx.amount (%s) for reference %s",
                returned_amount, self.amount, self.reference
            )

        if not self.snappay_payment_token:
            # بدون توکن نمی‌توان verify/revert کرد
            raise ValidationError("SnappPay: " + _("Missing payment token on transaction."))

        if state == 'OK':
            # verify_res = provider.snappay_verify(self.snappay_payment_token)
            self._set_done()
            return
        else:
            _logger.warning("SnappPay: Unknown state '%s' for reference %s", state, self.reference)
            self._set_error(_("Unknown payment state received: %s") % state)
            self._set_canceled()

    def _snappay_verify(self):
        """POST /api/online/payment/v1/verify با paymentToken"""
        self.ensure_one()
        if self.provider_code != 'snappay':
            raise ValidationError(_("Wrong provider for _snappay_verify"))
        token = self.snappay_payment_token or self.provider_reference
        if not token:
            raise ValidationError(_("Missing SnappPay payment token on transaction."))

        self.provider_id.snappay_verify(token,self)


    # def _snappay_settle(self):
    #     """POST /api/online/payment/v1/settle (بعداً، پایان روز)"""
    #     self.ensure_one()
    #     if self.provider_code != 'snappay':
    #         raise ValidationError(_("Wrong provider for _snappay_settle"))
    #     token = self.snappay_payment_token or self.provider_reference
    #     if not token:
    #         raise ValidationError(_("Missing SnappPay payment token on transaction."))
    #     # self.provider_id._snappay_request('/api/online/payment/v1/settle', {
    #     #     'paymentToken': token
    #     # })
    #     try:
    #         res = self.provider_id.snappay_settle(token)
    #         if not (res or {}).get('successful'):
    #             for sale in self.sale_order_ids:
    #                 sale.settle_status = res
    #         else:
    #             for sale in self.sale_order_ids:
    #                 sale.settle_status = res
    #
    #     except Exception:
    #         for sale in self.sale_order_ids:
    #             sale.settle_status = res
    #         self._set_error(_("Payment Settle failed."))

    def snappay_update_payment(self):

        self.ensure_one()
        if self.provider_id.code != 'snappay':
            raise UserError(_("SnappPay: wrong provider."))



        cart_item = []
        for line in self.sale_order_ids.order_line.filtered(lambda l: l.product_id.type == 'consu' and l.product_uom_qty>0):
            cart_item.append(
                {
                    "id": line.id,
                    "name": line.product_id.name,
                    "category": line.product_id.categ_id.name,
                    "count": line.product_uom_qty,
                     'commissionType': 100,
                    "amount": 10*int(round(line.price_unit, 0))
                })

        delivery_amount = sum(self.sale_order_ids.order_line.filtered(lambda l: l.is_delivery).mapped("price_total"))
        t_amount = sum(self.sale_order_ids.mapped("amount_total"))
        line_amount= sum(self.sale_order_ids.order_line.filtered(lambda l:l.product_id.type=='consu' and l.product_uom_qty>0).mapped("price_total"))
        disc_amount =abs(sum(self.sale_order_ids.order_line.filtered(lambda l:l.price_unit < 0).mapped("price_total")))


        cart_list = [{
            "cartId": self.sale_order_ids[0].id,
            "cartItems": cart_item,
            "isShipmentIncluded": True,
            'isTaxIncluded': True,
            "shippingAmount": 10*delivery_amount,
            "taxAmount": 0,
            "totalAmount": 10*int(round(t_amount, 0)+disc_amount),
        }]

        transaction_id = self.snappay_transaction_id
        mobile = (self.partner_id.phone or self.partner_id.mobile or "").strip()
        if mobile:
            if mobile.startswith('0'):
                mobile = '+98' + mobile[1:]
            elif not mobile.startswith('+98'):
                mobile = '+98' + mobile
        else:
            _logger.warning("SnappPay: partner %s has no mobile, using default test number", self.partner_id)
            mobile = '+989000000000'
        body = {
            "amount": 10*int(t_amount),
            "cartList": cart_list,
            "discountAmount":10* disc_amount,
            "externalSourceAmount":  0,
            "transactionId": transaction_id,
            "paymentMethodTypeDto": 'INSTALLMENT',
            'paymentToken':self.snappay_payment_token,


        }

        res = self.provider_id._snappay_request('/api/online/payment/v1/update', json_body=body, method='POST')
        if not (res or {}).get('successful'):
            raise UserError(_("SnappPay update failed: %s") % (res,))

    def snappay_cancel_payment(self, timeout=60):

        self.ensure_one()
        if self.provider_id.code != 'snappay':
            raise UserError(_("SnappPay: wrong provider."))

        res = self.provider_id._snappay_request('/api/online/payment/v1/cancel', json_body={"paymentToken": self.snappay_payment_token}, method='POST')
        if not (res or {}).get('successful'):
            raise UserError(_("SnappPay Cancel failed: %s") % (res,))







