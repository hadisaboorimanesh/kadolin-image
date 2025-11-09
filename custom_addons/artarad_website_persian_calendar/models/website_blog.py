# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
from odoo.tools.misc import get_lang

import jdatetime


class BlogPost(models.Model):
    _inherit = "blog.post"


    def get_formatted_date(self, date):
        if get_lang(self.env).code == "fa_IR":
            return jdatetime.datetime.fromgregorian(date=date).strftime("%Y/%m/%d")
        else:
            return date.strftime("%Y/%m/%d")