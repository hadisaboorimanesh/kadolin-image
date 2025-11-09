# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _

from odoo.tools.misc import babel_locale_parse, get_lang
from odoo.tools import posix_to_ldml

import datetime
import jdatetime
import babel.dates
from odoo.tools import posix_to_ldml, float_utils, format_date, format_duration, pycompat


class DateConverter(models.AbstractModel):
    _inherit = 'ir.qweb.field.date'

    def _format_date_jalali(self, value, options=None):
        if not value:
            return ''
        if not options:
            options = {}

        try:
            jdate = jdatetime.date.fromgregorian(date=value)
            fmt = options.get('format') or "%Y/%m/%d"
            jalali_str = jdate.strftime(fmt)
            return jalali_str
        except Exception as e:
            return format_date(self.env, value, date_format=options.get('format'))

    @api.model
    def value_to_html(self, value, options):
        if get_lang(self.env).code == "fa_IR":
            return self._format_date_jalali(value,options)
        return format_date(self.env, value, date_format=options.get('format'))

    # @api.model
    # def value_to_html(self, value, options):
    #     if get_lang(self.env).code == "fa_IR":
    #         if not value:
    #             return ''
    #         if isinstance(value, str):
    #             value = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    #
    #         fmt_tokens = []
    #         if any(token in options.get('format',[]) for token in ('y', 'Y')):
    #             fmt_tokens.append('%Y')
    #         if any(token in options.get('format',[]) for token in ('m', 'M')):
    #             fmt_tokens.append('%m')
    #         if any(token in options.get('format',[]) for token in ('d', 'D')):
    #             fmt_tokens.append('%d')
    #
    #         return jdatetime.datetime.fromgregorian(date=value).strftime('/'.join(fmt_tokens))
    #     return super(DateConverter, self).value_to_html(value, options)


class DateTimeConverter(models.AbstractModel):
    _inherit = 'ir.qweb.field.datetime'

    @api.model
    def value_to_html(self, value, options):
        if get_lang(self.env).code == "fa_IR":
            if not value:
                return ''
            if isinstance(value, str):
                value = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

            options = options or {}

            lang = self.user_lang()
            locale = babel_locale_parse(lang.code)
            format_func = babel.dates.format_datetime

            value = fields.Datetime.context_timestamp(self, value)

            if options.get('tz_name'):
                tzinfo = babel.dates.get_timezone(options['tz_name'])
            else:
                tzinfo = None

            if 'format' in options:
                pattern = options['format']
            else:
                if options.get('time_only'):
                    strftime_pattern = (u"%s" % (lang.time_format))
                elif options.get('date_only'):
                    strftime_pattern = (u"%s" % (lang.date_format))
                else:
                    strftime_pattern = (u"%s %s" % (lang.date_format, lang.time_format))

                pattern = posix_to_ldml(strftime_pattern, locale=locale)

            if options.get('hide_seconds'):
                pattern = pattern.replace(":ss", "").replace(":s", "")

            jvalue = jdatetime.datetime.fromgregorian(datetime=value)

            if options.get('time_only'):
                return jvalue.strftime("%H:%M:%S")
            elif options.get('date_only'):
                return jvalue.strftime("%Y/%m/%d")
            else:
                return jvalue.strftime("%Y/%m/%d %H:%M:%S")

        else:
            return super(DateTimeConverter, self).value_to_html(value, options)