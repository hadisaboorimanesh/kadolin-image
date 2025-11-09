# -*- coding: utf-8 -*-
from odoo import models
from odoo.tools.misc import get_lang

import jdatetime


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _portal_message_format(self, properties_names, options=None):
        vals_list = super(MailMessage, self)._portal_message_format(properties_names)
        if get_lang(self.env).code == "fa_IR":
            for vals in vals_list:
                vals['published_date_str'] = jdatetime.datetime.fromgregorian(datetime=vals['date']).strftime("%Y/%m/%d %H:%M:%S")
        return vals_list