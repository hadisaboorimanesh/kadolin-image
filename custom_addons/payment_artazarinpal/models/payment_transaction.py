# coding: utf-8
from odoo import models, fields, api, exceptions, _
from ..controllers.main import ZarinpalController

from werkzeug import urls
import requests
import json


class ZarinpalPaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'zarinpal':
            return res
        
        so_id = self.env['sale.order'].search([('name', '=', processing_values['reference'].split('-')[0])])
        base_url = self.provider_id.get_base_url()
        # base_url = "https://kadolin.ir"
        request_url = "https://api.zarinpal.com/pg/v4/payment/request.json"
        response = requests.post(request_url, json={"merchant_id": self.provider_id.zarinpal_merchant_id,
                                                    "amount": int(processing_values['amount'])*10,
                                                    "description": so_id.name,
                                                    "callback_url": urls.url_join(base_url, ZarinpalController._return_url)})

        rendering_values = processing_values.copy()
        if response.status_code == 200:
            authority = json.loads(response.text)["data"]["authority"]
            self.reference = authority
            rendering_values.update({
                'api_url': self.provider_id._zarinpal_get_api_url() + authority,
                'redirect_url':base_url
            })
        return rendering_values

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'zarinpal':
            return tx

        reference = notification_data.get('Authority')
        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'zarinpal')])
        if not tx:
            raise exceptions.ValidationError(
                "Zarinpal: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        if self.provider_code != 'zarinpal':
            return
        
        status = notification_data.get('Status')
        if status == 'OK':
            self._set_pending()

            so_id = self.sale_order_ids
            request_url = "https://api.zarinpal.com/pg/v4/payment/verify.json"
            response = requests.post(request_url, json={"merchant_id": self.provider_id.zarinpal_merchant_id,
                                                        "amount": int(so_id.amount_total)*10,
                                                        "authority": notification_data.get('Authority')})

            if json.loads(response.text)["data"]["code"] in (100, 101):
                 self._set_done()
                 return True
            else:
                self._set_canceled()
                return False
        else:
            self._set_canceled()