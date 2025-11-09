from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ..controllers.main import MellatController

from werkzeug import urls
import datetime
import pytz
from zeep import Client

class mellatPaymentTransaction(models.Model):
    _inherit = 'payment.transaction'


    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != "mellat":
            return res

        local_datetime_obj = datetime.datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.timezone("Asia/Tehran"))
        so_id = self.env['sale.order'].search([('name','=', processing_values['reference'].split('-')[0])])
        orderId = int(local_datetime_obj.strftime('%Y%m%d%H%M%S') + str(so_id.id))
        paymentAmount = int(processing_values['amount'])*10

        # url = self.provider_id._mellat_get_api_url()
        # cli = Client(url)
        wsdl_url = 'https://bpm.shaparak.ir/pgwchannel/services/pgw?wsdl'  # ← برای Zeep
        startpay_url = 'https://bpm.shaparak.ir/pgwchannel/startpay.mellat'  # ← برای redirect

        cli = Client(wsdl=wsdl_url)
        response = cli.service.bpPayRequest(terminalId=self.provider_id.mellat_terminal_id,
                                            userName=self.provider_id.mellat_username,
                                            userPassword=self.provider_id.mellat_password,
                                            orderId=orderId,
                                            amount=paymentAmount,
                                            localDate=local_datetime_obj.strftime('%Y%m%d'),
                                            localTime=local_datetime_obj.strftime('%H%M%S'),
                                            additionalData="{};{};{}".format(self.provider_id.mellat_terminal_id, so_id.id, paymentAmount),
                                            callBackUrl=urls.url_join(self.provider_id.get_base_url(), MellatController._return_url),
                                            payerId=0
                                            )

        rendering_values = {
            'api_url': self.provider_id._mellat_get_api_url()
        }

        if response.split(',')[0] == '0': # OK
            RefId = response.split(',')[1]
            self.provider_reference = RefId
            rendering_values.update({'RefId': RefId})

        return rendering_values


    def _get_tx_from_notification_data(self, provider_code, notification_data):
        if provider_code != 'mellat':
            return super()._get_tx_from_notification_data(provider_code, notification_data)

        reference = notification_data.get('RefId')
        tx = self.search([('provider_reference', '=', reference), ('provider_code', '=', 'mellat')])
        if not tx:
            raise ValidationError(
                "Mellat: " + _("No transaction found matching reference %s.", reference)
            )
        return tx


    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        if self.provider_code != 'mellat':
            return
        
        self._set_pending()
        
        ResCode = notification_data["ResCode"]
        if ResCode == '0': # OK
            url = 'https://bpm.shaparak.ir/pgwchannel/services/pgw?wsdl'
            cli = Client(url)
            response = cli.service.bpVerifyRequest(terminalId=self.provider_id.mellat_terminal_id,
                                                    userName=self.provider_id.mellat_username,
                                                    userPassword=self.provider_id.mellat_password,
                                                    orderId=notification_data.get("SaleOrderId"),
                                                    saleOrderId=notification_data.get("SaleOrderId"),
                                                    saleReferenceId=notification_data.get("SaleReferenceId")
                                                    )
            if response == '0':
                self._set_done()
                return True
            else:
                self._set_canceled()
                return False
        else:
            self._set_canceled()
            return False