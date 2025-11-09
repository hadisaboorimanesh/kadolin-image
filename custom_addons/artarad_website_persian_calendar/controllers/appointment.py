# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.appointment.controllers import appointment 
from odoo.tools.misc import get_lang
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as dtf
from odoo.tools import is_html_empty

import jdatetime
from werkzeug.exceptions import NotFound
from urllib.parse import unquote_plus
from datetime import datetime
from babel.dates import format_datetime, format_date, format_time
import json


_formated_weekdays_original = appointment._formated_weekdays
def _formated_weekdays(locale):
    if get_lang(request.env).code == "fa_IR":
        return jdatetime.date.j_weekdays_fa
    else:
        return _formated_weekdays_original(locale)
appointment._formated_weekdays = _formated_weekdays


class artaradAppointmentController(appointment.AppointmentController):
    @http.route(['/appointment/<int:appointment_type_id>/info'],
                type='http', auth="public", website=True, sitemap=False)
    def appointment_type_id_form(self, appointment_type_id, date_time, duration, staff_user_id=None, resource_selected_id=None, available_resource_ids=None, asked_capacity=1, **kwargs):
        """
        Render the form to get information about the user for the appointment

        :param appointment_type_id: the appointment type id related
        :param date_time: the slot datetime selected for the appointment
        :param duration: the duration of the slot
        :param staff_user_id: the user selected for the appointment
        :param resource_selected_id: the resource selected for the appointment
        :param available_resource_ids: the resources info we want to propagate that are linked to the slot time
        :param asked_capacity: the asked capacity for the appointment
        :param filter_appointment_type_ids: see ``Appointment.appointments()`` route
        """
        if get_lang(request.env).code == "fa_IR":
            domain = self._appointments_base_domain(
                filter_appointment_type_ids=kwargs.get('filter_appointment_type_ids'),
                search=kwargs.get('search'),
                invite_token=kwargs.get('invite_token')
            )
            available_appointments = self._fetch_and_check_private_appointment_types(
                kwargs.get('filter_appointment_type_ids'),
                kwargs.get('filter_staff_user_ids'),
                kwargs.get('filter_resource_ids'),
                kwargs.get('invite_token'),
                domain=domain,
            )
            appointment_type = available_appointments.filtered(lambda appt: appt.id == int(appointment_type_id))

            if not appointment_type:
                raise NotFound()

            if not self._check_appointment_is_valid_slot(appointment_type, staff_user_id, resource_selected_id, available_resource_ids, date_time, duration, asked_capacity, **kwargs):
                raise NotFound()

            partner = self._get_customer_partner()
            partner_data = partner.read(fields=['name', 'phone', 'email'])[0] if partner else {}
            date_time = unquote_plus(date_time)
            date_time_object = datetime.strptime(date_time, dtf)
            ########## overrided ##########
            j_date_time_object = jdatetime.datetime.fromgregorian(datetime=date_time_object)
            ########## ######### ##########
            day_name = format_datetime(date_time_object, 'EEE', locale=get_lang(request.env).code)
            date_formated = format_date(date_time_object.date(), locale=get_lang(request.env).code)
            time_locale = format_time(date_time_object.time(), locale=get_lang(request.env).code, format='short')
            resource = request.env['appointment.resource'].sudo().browse(int(resource_selected_id)) if resource_selected_id else request.env['appointment.resource']
            staff_user = request.env['res.users'].browse(int(staff_user_id)) if staff_user_id else request.env['res.users']
            users_possible = self._get_possible_staff_users(
                appointment_type,
                json.loads(unquote_plus(kwargs.get('filter_staff_user_ids') or '[]')),
            )
            resources_possible = self._get_possible_resources(
                appointment_type,
                json.loads(unquote_plus(kwargs.get('filter_resource_ids') or '[]')),
            )
            return request.render("appointment.appointment_form", {
                'partner_data': partner_data,
                'appointment_type': appointment_type,
                'available_appointments': available_appointments,
                'main_object': appointment_type,
                'datetime': date_time,
                # 'date_locale': f'{day_name} {date_formated}',
                'date_locale': f"{jdatetime.date.j_weekdays_fa[j_date_time_object.weekday()]} {j_date_time_object.day} {jdatetime.date.j_months_fa[j_date_time_object.month - 1]} {j_date_time_object.year}",
                'time_locale': time_locale,
                'datetime_str': date_time,
                'duration_str': duration,
                'duration': float(duration),
                'staff_user': staff_user,
                'resource': resource,
                'asked_capacity': int(asked_capacity),
                'timezone': request.session.get('timezone') or appointment_type.appointment_tz,  # bw compatibility
                'users_possible': users_possible,
                'resources_possible': resources_possible,
                'available_resource_ids': available_resource_ids,
            })
        else:
            return super(artaradAppointmentController, self).appointment_type_id_form(appointment_type_id, date_time, duration, staff_user_id, resource_selected_id, available_resource_ids, asked_capacity, **kwargs)


    def _get_appointment_type_page_view(self, appointment_type, page_values, state=False, **kwargs):
        """
        Renders the appointment information alongside the calendar for the slot selection, after computation of
        the slots and preparation of other values, depending on the arguments values. This is the method to override
        in order to select another view for the appointment page.

        :param appointment_type: the appointment type that we want to access.
        :param page_values: dict containing common appointment page values. See _prepare_appointment_type_page_values for details.
        :param state: the type of message that will be displayed in case of an error/info. See appointment_type_page.
        """
        if get_lang(request.env).code == "fa_IR":
            request.session.timezone = self._get_default_timezone(appointment_type)
            filter_users = page_values['user_selected'] or page_values['user_default'] or page_values['users_possible'] \
                if appointment_type.schedule_based_on == "users" else None
            filter_resources = page_values['resource_selected'] or page_values['resource_default'] or page_values['resources_possible'] \
                if appointment_type.schedule_based_on == "resources" else None
            asked_capacity = int(kwargs.get('asked_capacity', 1))
            slots = appointment_type._get_appointment_slots(
                request.session['timezone'],
                filter_users=filter_users,
                filter_resources=filter_resources,
                asked_capacity=asked_capacity,
            )
            formated_days = _formated_weekdays(get_lang(request.env).code)
            month_first_available = next((month['id'] for month in slots if month['has_availabilities']), False)

            render_params = dict({
                'appointment_type': appointment_type,
                'is_html_empty': is_html_empty,
                'formated_days': formated_days,
                'main_object': appointment_type,
                'month_first_available': month_first_available,
                'month_kept_from_update': False,
                'slots': slots,
                'state': state,
                'timezone': request.session['timezone'],  # bw compatibility
            }, **page_values
            )
            # Do not let the browser store the page, this ensures correct timezone and params management in case
            # the user goes back and forth to this endpoint using browser controls (or mouse back button)
            # this is especially necessary as we alter the request.session parameters.
            return request.render("appointment.appointment_info", render_params, headers={'Cache-Control': 'no-store'})
        else:
            return super(artaradAppointmentController, self)._get_appointment_type_page_view(appointment_type, page_values, state, **kwargs)