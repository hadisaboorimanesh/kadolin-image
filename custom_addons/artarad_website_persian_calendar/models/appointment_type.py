# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _

import pytz
import calendar as cal
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import babel_locale_parse, get_lang
from babel.dates import format_time
from werkzeug.urls import url_encode

import jdatetime


class jdate_utils:
    @staticmethod
    def get_month(date):
        date_from = jdatetime.date(date.year, date.month, 1)

        if date.month <= 6:
            date_to = jdatetime.date(date.year, date.month, 31)
        elif date.month <= 11:
            date_to = jdatetime.date(date.year, date.month, 30)
        else:
            if date.isleap():
                date_to = jdatetime.date(date.year, date.month, 30)
            else:
                date_to = jdatetime.date(date.year, date.month, 29)
        return date_from, date_to

    @staticmethod
    def get_month_dates_calendar(date):
        start, end = jdate_utils.get_month(date)

        while start.weekday() != 0:
            start -= jdatetime.timedelta(days=1)
        while end.weekday() != 0:
            end += jdatetime.timedelta(days=1)
           
        dates = [[] for _ in range((end - start).days // 7)]
        i = 0
        while start != end:
            dates[i//7].append(start)
            start += jdatetime.timedelta(days=1)
            i+=1
        
        return dates

class artaradAppointmentType(models.Model):
    _inherit = "appointment.type"


    def _get_appointment_slots(self, timezone, filter_users=None, filter_resources=None, asked_capacity=1, reference_date=None):
        """ Fetch available slots to book an appointment.

        :param str timezone: timezone string e.g.: 'Europe/Brussels' or 'Etc/GMT+1'
        :param <res.users> filter_users: filter available slots for those users (can be a singleton
        for fixed appointment types or can contain several users, e.g. with random assignment and
        filters) If not set, use all users assigned to this appointment type.
        :param <appointment.resource> filter_resources: filter available slots for those resources
        (can be a singleton for fixed appointment types or can contain several resources,
        e.g. with random assignment and filters) If not set, use all resources assigned to this
        appointment type.
        :param int asked_capacity: the capacity the user want to book.
        :param datetime reference_date: starting datetime to fetch slots. If not
        given now (in UTC) is used instead. Note that minimum schedule hours
        defined on appointment type is added to the beginning of slots;

        :returns: list of dicts (1 per month) containing available slots per week
        and per day for each week (see ``_slots_generate()``), like
        [
            {'id': 0,
            'month': 'February 2022' (formatted month name),
            'weeks': [
                [{'day': '']
                [{...}],
            ],
            },
            {'id': 1,
            'month': 'March 2022' (formatted month name),
            'weeks': [ (...) ],
            },
            {...}
        ]
        """
        if get_lang(self.env).code == "fa_IR":
            self.ensure_one()

            if not self.active:
                return []
            now = datetime.utcnow()
            if not reference_date:
                reference_date = now

            requested_tz = pytz.timezone(timezone)

            appointment_duration_days = self.max_schedule_days
            unique_slots = self.slot_ids.filtered(lambda slot: slot.slot_type == 'unique')

            if self.category == 'custom' and unique_slots:
                # Custom appointment type, the first day should depend on the first slot datetime
                start_first_slot = unique_slots[0].start_datetime
                first_day_utc = start_first_slot if reference_date > start_first_slot else reference_date
                first_day = requested_tz.fromutc(first_day_utc + relativedelta(hours=self.min_schedule_hours))
                appointment_duration_days = (unique_slots[-1].end_datetime.date() - reference_date.date()).days
                last_day = requested_tz.fromutc(reference_date + relativedelta(days=appointment_duration_days))
            elif self.category == 'punctual':
                # Punctual appointment type, the first day is the start_datetime if it is in the future, else the first day is now
                reference_date = self.start_datetime if self.start_datetime > now else now
                first_day = requested_tz.fromutc(reference_date)
                last_day = requested_tz.fromutc(self.end_datetime)
            else:
                # Recurring appointment type
                first_day = requested_tz.fromutc(reference_date + relativedelta(hours=self.min_schedule_hours))
                last_day = requested_tz.fromutc(reference_date + relativedelta(days=appointment_duration_days))

            # Compute available slots (ordered)
            slots = self._slots_generate(
                first_day.astimezone(pytz.utc),
                last_day.astimezone(pytz.utc),
                timezone,
                reference_date=reference_date
            )

            # No slots -> skip useless computation
            if not slots:
                return slots
            valid_users = filter_users.filtered(lambda user: user in self.staff_user_ids) if filter_users else None
            valid_resources = filter_resources.filtered(lambda resource: resource in self.resource_ids) if filter_resources else None
            # Not found staff user : incorrect configuration -> skip useless computation
            if filter_users and not valid_users:
                return []
            if filter_resources and not valid_resources:
                return []
            if self.schedule_based_on == 'users':
                self._slots_fill_users_availability(
                    slots,
                    first_day.astimezone(pytz.UTC),
                    last_day.astimezone(pytz.UTC),
                    valid_users,
                )
                slot_field_label = 'staff_user_id'
            else:
                self._slots_fill_resources_availability(
                    slots,
                    first_day.astimezone(pytz.UTC),
                    last_day.astimezone(pytz.UTC),
                    valid_resources,
                    asked_capacity,
                )
                slot_field_label = 'available_resource_ids'

            total_nb_slots = sum(slot_field_label in slot for slot in slots)
            # If there is no slot for the minimum capacity then we return an empty list.
            # This will lead to a screen informing the customer that there is no availability.
            # We don't want to return an empty list if the capacity as been tempered by the customer
            # as he should still be able to interact with the screen and select another capacity.
            if not total_nb_slots and asked_capacity == 1:
                return []
            nb_slots_previous_months = 0

            # Compute calendar rendering and inject available slots
            today = requested_tz.fromutc(reference_date)
            start = slots[0][timezone][0] if slots else today
            locale = babel_locale_parse(get_lang(self.env).code)
            month_dates_calendar = cal.Calendar(locale.first_week_day).monthdatescalendar
            months = []
            while (start.year, start.month) <= (last_day.year, last_day.month):
                nb_slots_next_months = sum(slot_field_label in slot for slot in slots)
                has_availabilities = False
                ########## Overrided ##########
                # dates = month_dates_calendar(start.year, start.month)
                j_start = jdatetime.datetime.fromgregorian(datetime=start)
                dates = jdate_utils.get_month_dates_calendar(j_start)
                for i in range(len(dates)):
                    for j in range(len(dates[i])):
                        dates[i][j] = dates[i][j].togregorian()
                ########## ######### ##########
                for week_index, week in enumerate(dates):
                    for day_index, day in enumerate(week):
                        mute_cls = weekend_cls = today_cls = None
                        today_slots = []
                        ########## Overrided ##########
                        # if day.weekday() in (cal.SUNDAY, cal.SATURDAY):
                        #     weekend_cls = 'o_weekend'
                        # if day == today.date() and day.month == today.month:
                        #     today_cls = 'o_today'
                        # if day.month != start.month:
                        #     mute_cls = 'text-muted o_mute_day'
                        j_day = jdatetime.datetime.fromgregorian(datetime=day)
                        j_today = jdatetime.datetime.fromgregorian(datetime=today)
                        if j_day.weekday() in (6,):
                            weekend_cls = 'o_weekend'
                        if j_day.date() == j_today.date() and j_day.month == j_today.month:
                            today_cls = 'o_today'
                        if j_day.month != j_start.month:
                            mute_cls = 'text-muted o_mute_day'
                        ########## ######### ##########
                        else:
                            # slots are ordered, so check all unprocessed slots from until > day
                            while slots and (slots[0][timezone][0].date() <= day):
                                if (slots[0][timezone][0].date() == day) and ('staff_user_id' in slots[0]):
                                    slot_staff_user_id = slots[0]['staff_user_id'].id
                                    slot_start_dt_tz = slots[0][timezone][0].strftime('%Y-%m-%d %H:%M:%S')
                                    slot = {
                                        'datetime': slot_start_dt_tz,
                                        'staff_user_id': slot_staff_user_id,
                                    }
                                    if slots[0]['slot'].allday:
                                        slot_duration = 24
                                        slot.update({
                                            'hours': _("All day"),
                                            'slot_duration': slot_duration,
                                        })
                                    else:
                                        start_hour = format_time(slots[0][timezone][0].time(), format='short', locale=locale)
                                        end_hour = format_time(slots[0][timezone][1].time(), format='short', locale=locale)
                                        slot_duration = str((slots[0][timezone][1] - slots[0][timezone][0]).total_seconds() / 3600)
                                        slot.update({
                                            'hours': "%s - %s" % (start_hour, end_hour) if self.category == 'custom' else start_hour,
                                            'slot_duration': slot_duration,
                                        })
                                    slot['url_parameters'] = url_encode({
                                        'staff_user_id': slot_staff_user_id,
                                        'date_time': slot_start_dt_tz,
                                        'duration': slot_duration,
                                    })
                                    today_slots.append(slot)
                                    nb_slots_next_months -= 1
                                slots.pop(0)
                        today_slots = sorted(today_slots, key=lambda d: d['datetime'])
                        dates[week_index][day_index] = {
                            'day': day,
                            ########## overrided ##########
                            'j_day': jdatetime.datetime.fromgregorian(datetime=day).day,
                            ########## ######### ##########
                            'slots': today_slots,
                            'mute_cls': mute_cls,
                            'weekend_cls': weekend_cls,
                            'today_cls': today_cls
                        }

                        has_availabilities = has_availabilities or bool(today_slots)

                months.append({
                    'id': len(months),
                    # 'month': format_datetime(start, 'MMMM Y', locale=get_lang(self.env).code),
                    'month': j_start.strftime("%Y ") + jdatetime.date.j_months_fa[j_start.month - 1],
                    'weeks': dates,
                    'has_availabilities': has_availabilities,
                    'nb_slots_previous_months': nb_slots_previous_months,
                    'nb_slots_next_months': nb_slots_next_months,
                })
                nb_slots_previous_months = total_nb_slots - nb_slots_next_months
                ########## overrided #########
                # start = start + relativedelta(months=1)
                if j_start.month == 6 and j_start.day == 31:
                    j_start = j_start.replace(month=7, day=30)
                elif j_start.month == 11 and j_start.day == 30:
                    j_start = j_start.replace(month=12, day=30 if j_start.isleap() else 29)
                elif j_start.month == 12:
                    j_start = j_start.replace(year=j_start.year + 1, month=1, day=31 if j_start.day in [29, 30] else j_start.day)
                else:
                    j_start = j_start.replace(month=j_start.month + 1)

                start = j_start.togregorian()
                ########## ######### #########
            return months
        else:
            return super(artaradAppointmentType, self)._get_appointment_slots(timezone, filter_users, filter_resources, asked_capacity, reference_date)
