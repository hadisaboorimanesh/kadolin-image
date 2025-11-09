# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request, route
from odoo.addons.appointment.controllers import calendar 
from odoo.tools.misc import get_lang
from odoo.tools import is_html_empty

import jdatetime
import pytz
from babel.dates import format_datetime, format_date
from werkzeug.urls import url_encode



class AppointmentCalendarController(calendar.CalendarController):
    @route(['/calendar/view/<string:access_token>'], type='http', auth="public", website=True)
    def appointment_view(self, access_token, partner_id, state=False, **kwargs):
        """
        Render the validation of an appointment and display a summary of it

        :param access_token: the access_token of the event linked to the appointment
        :param state: allow to display an info message, possible values:
            - new: Info message displayed when the appointment has been correctly created
            - no-cancel: Info message displayed when an appointment can no longer be canceled
        """
        if get_lang(request.env).code == "fa_IR":
            partner_id = int(partner_id)
            event = request.env['calendar.event'].sudo().search([('access_token', '=', access_token)], limit=1)
            if not event:
                return request.not_found()
            timezone = request.session.get('timezone')
            if not timezone:
                timezone = request.env.context.get('tz') or event.appointment_type_id.appointment_tz or event.partner_ids and event.partner_ids[0].tz or event.user_id.tz or 'UTC'
                request.session['timezone'] = timezone
            tz_session = pytz.timezone(timezone)

            date_start_suffix = ""
            format_func = format_datetime
            if not event.allday:
                url_date_start = fields.Datetime.from_string(event.start).strftime('%Y%m%dT%H%M%SZ')
                url_date_stop = fields.Datetime.from_string(event.stop).strftime('%Y%m%dT%H%M%SZ')
                date_start = fields.Datetime.from_string(event.start).replace(tzinfo=pytz.utc).astimezone(tz_session)
            else:
                url_date_start = url_date_stop = fields.Date.from_string(event.start_date).strftime('%Y%m%d')
                date_start = fields.Date.from_string(event.start_date)
                format_func = format_date
                date_start_suffix = _(', All Day')

            locale = get_lang(request.env).code
            day_name = format_func(date_start, 'EEE', locale=locale)
            ########## overrided ##########
            # date_start = day_name + ' ' + format_func(date_start, locale=locale) + date_start_suffix
            j_date_start = jdatetime.datetime.fromgregorian(datetime=date_start)
            date_start = f"{jdatetime.date.j_weekdays_fa[j_date_start.weekday()]} {j_date_start.day} {jdatetime.date.j_months_fa[j_date_start.month - 1]} {j_date_start.year}, {j_date_start.strftime('%H:%M')}"
            ########## ######### ##########
            params = {
                'action': 'TEMPLATE',
                'text': event._get_customer_summary(),
                'dates': f'{url_date_start}/{url_date_stop}',
                'details': event._get_customer_description(),
            }
            if event.location:
                params.update(location=event.location.replace('\n', ' '))
            encoded_params = url_encode(params)
            google_url = 'https://www.google.com/calendar/render?' + encoded_params

            return request.render("appointment.appointment_validated", {
                'event': event,
                'datetime_start': date_start,
                'google_url': google_url,
                'state': state,
                'partner_id': partner_id,
                'attendee_status': event.attendee_ids.filtered(lambda a: a.partner_id.id == partner_id).state,
                'is_html_empty': is_html_empty,
            })
        else:
            return super(AppointmentCalendarController, self).appointment_view(access_token, partner_id, state, **kwargs)