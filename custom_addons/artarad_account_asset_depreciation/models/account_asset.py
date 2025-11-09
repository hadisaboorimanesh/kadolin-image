# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
from odoo.tools import float_is_zero

from dateutil.relativedelta import relativedelta
import jdatetime

DAYS_PER_MONTH = 30
DAYS_PER_YEAR = DAYS_PER_MONTH * 12

def get_end_of_jalaali_month(date):
    jdate = jdatetime.datetime.fromgregorian(date=date).date()
    end_of_jalali_month = jdate
    # 1- go to the beginning of next month
    while (end_of_jalali_month.month == jdate.month):
        end_of_jalali_month += jdatetime.timedelta(days=1)

    # 2- go back to previous day
    end_of_jalali_month -= jdatetime.timedelta(days=1)

    return end_of_jalali_month.togregorian()


class artaradAccountAsset(models.Model):
    _inherit = 'account.asset'


    def _recompute_board(self, start_depreciation_date=False):
        if self.env.company.account_asset_depreciation_calendar_type == "jalaali":
            self.ensure_one()
            # All depreciation moves that are posted
            posted_depreciation_move_ids = self.depreciation_move_ids.filtered(
                lambda mv: mv.state == 'posted' and not mv.asset_value_change
            ).sorted(key=lambda mv: (mv.date, mv.id))

            imported_amount = self.already_depreciated_amount_import
            residual_amount = self.value_residual
            if not posted_depreciation_move_ids:
                residual_amount += imported_amount
            residual_declining = residual_amount

            start_depreciation_date = start_depreciation_date or self.paused_prorata_date
            ########## overrided ##########
            # if not self.parent_id:
            #     final_depreciation_date = self.paused_prorata_date + relativedelta(months=int(self.method_period) * self.method_number, days=-1)
            # else:
            #     # If it has a parent, we want the increase only for the remaining days the parent has
            #     final_depreciation_date = self.parent_id.paused_prorata_date + relativedelta(months=int(self.parent_id.method_period) * self.parent_id.method_number, days=-1)

            # final_depreciation_date = self._get_end_period_date(final_depreciation_date)
            dt = start_depreciation_date = start_depreciation_date + relativedelta(days=1)
            for _ in range(int(self.method_period) * self.method_number):
                dt = get_end_of_jalaali_month(dt)
                dt += relativedelta(days=1)
            dt -= relativedelta(days=1)
            final_depreciation_date = dt
            ########## ######### ##########
    
            depreciation_move_values = []
            if not float_is_zero(self.value_residual, precision_rounding=self.currency_id.rounding):
                while not self.currency_id.is_zero(residual_amount) and start_depreciation_date < final_depreciation_date:
                    period_end_depreciation_date = self._get_end_period_date(start_depreciation_date)
                    period_end_fiscalyear_date = self.company_id.compute_fiscalyear_dates(period_end_depreciation_date).get('date_to')

                    days, amount = self._compute_board_amount(residual_amount, start_depreciation_date, period_end_depreciation_date, False, False, residual_declining)
                    residual_amount -= amount

                    if not posted_depreciation_move_ids:
                        # self.already_depreciated_amount_import management.
                        # Subtracts the imported amount from the first depreciation moves until we reach it
                        # (might skip several depreciation entries)
                        if abs(imported_amount) <= abs(amount):
                            amount -= imported_amount
                            imported_amount = 0
                        else:
                            imported_amount -= amount
                            amount = 0

                    if self.method == 'degressive_then_linear' and final_depreciation_date < period_end_depreciation_date:
                        period_end_depreciation_date = final_depreciation_date

                    if not float_is_zero(amount, precision_rounding=self.currency_id.rounding):
                        # For deferred revenues, we should invert the amounts.
                        depreciation_move_values.append(self.env['account.move']._prepare_move_for_asset_depreciation({
                            'amount': amount,
                            'asset_id': self,
                            'depreciation_beginning_date': start_depreciation_date,
                            'date': period_end_depreciation_date,
                            'asset_number_days': days,
                        }))

                    if period_end_depreciation_date == period_end_fiscalyear_date:
                        residual_declining = residual_amount

                    start_depreciation_date = period_end_depreciation_date + relativedelta(days=1)

            return depreciation_move_values
        else:
            return super(artaradAccountAsset, self)._recompute_board(start_depreciation_date)

    def _get_end_period_date(self, start_depreciation_date):
        if self.env.company.account_asset_depreciation_calendar_type == "jalaali":
            self.ensure_one()
            fiscalyear_date = self.company_id.compute_fiscalyear_dates(start_depreciation_date).get('date_to')
            period_end_depreciation_date = fiscalyear_date if start_depreciation_date < fiscalyear_date else fiscalyear_date + relativedelta(years=1)
    
            if self.method_period == '1':  # If method period is set to monthly computation
                ########## overrided ##########
                # max_day_in_month = end_of(datetime.date(start_depreciation_date.year, start_depreciation_date.month, 1), 'month').day
                # period_end_depreciation_date = min(start_depreciation_date.replace(day=max_day_in_month), period_end_depreciation_date)
                # j_start_depreciation_date = jdatetime.datetime.fromgregorian(date=start_depreciation_date).date()
                period_end_depreciation_date = min(get_end_of_jalaali_month(start_depreciation_date), period_end_depreciation_date)
                ########## ######### ##########
            return period_end_depreciation_date
        else:
            return super(artaradAccountAsset, self)._get_end_period_date(start_depreciation_date)

    def _get_delta_days(self, start_date, end_date):
        if self.env.company.account_asset_depreciation_calendar_type == "jalaali":
            self.ensure_one()
            if self.prorata_computation_type == 'daily_computation':
                # Compute how many days there are between 2 dates using a daily_computation method
                return (end_date - start_date).days + 1
            else:
                # Compute how many days there are between 2 dates counting 30 days per month
                # Get how many days there are in the start date month
                ########## overrided ##########
                # start_date_days_month = end_of(start_date, 'month').day
                start_date_days_month = jdatetime.datetime.fromgregorian(date=get_end_of_jalaali_month(start_date)).date().day
                ########## ######### ##########
                # Get how many days there are in the start date month (e.g: June 20th: (30 * (30 - 20 + 1)) / 30 = 11)
                ########## overrided ##########
                # start_prorata = (start_date_days_month - start_date.day + 1) / start_date_days_month
                start_prorata = (start_date_days_month - jdatetime.datetime.fromgregorian(date=start_date).day + 1) / start_date_days_month
                ########## ######### ##########
                # Get how many days there are in the end date month (e.g: You're the August 14th: (14 * 30) / 31 = 13.548387096774194)
                ########## overrided ##########
                # end_prorata = end_date.day / end_of(end_date, 'month').day
                end_prorata = jdatetime.datetime.fromgregorian(date=end_date).day / jdatetime.datetime.fromgregorian(date=get_end_of_jalaali_month(end_date)).date().day
                ########## ######### ##########
                # Compute how many days there are between these 2 dates
                # e.g: 13.548387096774194 + 11 + 360 * (2020 - 2020) + 30 * (8 - 6 - 1) = 24.548387096774194 + 360 * 0 + 30 * 1 = 54.548387096774194 day
                return sum((
                    start_prorata * DAYS_PER_MONTH,
                    end_prorata * DAYS_PER_MONTH,
                    ########## overrided ##########
                    # (end_date.year - start_date.year) * DAYS_PER_YEAR,
                    # (end_date.month - start_date.month - 1) * DAYS_PER_MONTH,
                    (jdatetime.datetime.fromgregorian(date=end_date).year - jdatetime.datetime.fromgregorian(date=start_date).year) * DAYS_PER_YEAR,
                    (jdatetime.datetime.fromgregorian(date=end_date).month - jdatetime.datetime.fromgregorian(date=start_date).month - 1) * DAYS_PER_MONTH
                    ########## ######### ##########
                ))
        else:
            return super(artaradAccountAsset, self)._get_delta_days(start_date, end_date)