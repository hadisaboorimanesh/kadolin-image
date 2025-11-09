from odoo import models, fields, api, exceptions, _
from odoo.tools.misc import formatLang

import json
from odoo.tools.misc import formatLang, format_date as odoo_format_date, get_lang
from collections import defaultdict
from datetime import datetime, timedelta
from babel.dates import format_datetime, format_date
from odoo.release import version
import random
from odoo.osv import expression

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF, SQL

def group_by_journal(vals_list):
    res = defaultdict(list)
    for vals in vals_list:
        res[vals['journal_id']].append(vals)
    return res

class artarad_account_journal(models.Model):
    _inherit = "account.journal"



    @api.depends('current_statement_balance')
    def _kanban_dashboard_graph(self):
        bank_cash_journals = self.filtered(lambda journal: journal.type in ('bank', 'cash', 'credit','post_dated_cheque'))
        bank_cash_graph_datas = bank_cash_journals._get_bank_cash_graph_data()
        for journal in bank_cash_journals:
            journal.kanban_dashboard_graph = json.dumps(bank_cash_graph_datas[journal.id])

        sale_purchase_journals = self.filtered(lambda journal: journal.type in ('sale', 'purchase'))
        sale_purchase_graph_datas = sale_purchase_journals._get_sale_purchase_graph_data()
        for journal in sale_purchase_journals:
            journal.kanban_dashboard_graph = json.dumps(sale_purchase_graph_datas[journal.id])

        (self - bank_cash_journals - sale_purchase_journals).kanban_dashboard_graph = False

    def _fill_bank_cash_dashboard_data(self, dashboard_data):
        """Populate all bank and cash journal's data dict with relevant information for the kanban card."""
        bank_cash_journals = self.filtered(lambda journal: journal.type in ('bank', 'cash', 'credit','post_dated_cheque'))
        if not bank_cash_journals:
            return

        # Number to reconcile
        self._cr.execute("""
            SELECT st_line.journal_id,
                   COUNT(st_line.id)
              FROM account_bank_statement_line st_line
              JOIN account_move st_line_move ON st_line_move.id = st_line.move_id
             WHERE st_line.journal_id IN %s
               AND st_line.company_id IN %s
               AND NOT st_line.is_reconciled
               AND st_line_move.checked IS TRUE
               AND st_line_move.state = 'posted'
          GROUP BY st_line.journal_id
        """, [tuple(bank_cash_journals.ids), tuple(self.env.companies.ids)])
        number_to_reconcile = {
            journal_id: count
            for journal_id, count in self.env.cr.fetchall()
        }

        # Last statement
        bank_cash_journals.last_statement_id.mapped(lambda s: s.balance_end_real)  # prefetch

        outstanding_pay_account_balances = bank_cash_journals._get_journal_dashboard_outstanding_payments()

        # Payment with method outstanding account == journal default account
        direct_payment_balances = bank_cash_journals._get_direct_bank_payments()

        # Misc Entries (journal items in the default_account not linked to bank.statement.line)
        misc_domain = []
        for journal in bank_cash_journals:
            date_limit = journal.last_statement_id.date or journal.company_id.fiscalyear_lock_date
            misc_domain.append(
                [('account_id', '=', journal.default_account_id.id), ('date', '>', date_limit)]
                if date_limit else
                [('account_id', '=', journal.default_account_id.id)]
            )
        misc_domain = [
            *self.env['account.move.line']._check_company_domain(self.env.companies),
            ('statement_line_id', '=', False),
            ('parent_state', '=', 'posted'),
            ('payment_id', '=', False),
      ] + expression.OR(misc_domain)

        misc_totals = {
            account: (balance, count_lines, currencies)
            for account, balance, count_lines, currencies in self.env['account.move.line']._read_group(
                domain=misc_domain,
                aggregates=['amount_currency:sum', 'id:count', 'currency_id:recordset'],
                groupby=['account_id'])
        }

        # To check
        to_check = {
            journal: (amount, count)
            for journal, amount, count in self.env['account.bank.statement.line']._read_group(
                domain=[
                    ('journal_id', 'in', bank_cash_journals.ids),
                    ('move_id.company_id', 'in', self.env.companies.ids),
                    ('move_id.checked', '=', False),
                    ('move_id.state', '=', 'posted'),
                ],
                groupby=['journal_id'],
                aggregates=['amount:sum', '__count'],
            )
        }

        for journal in bank_cash_journals:
            # User may have read access on the journal but not on the company
            currency = journal.currency_id or self.env['res.currency'].browse(journal.company_id.sudo().currency_id.id)
            has_outstanding, outstanding_pay_account_balance = outstanding_pay_account_balances[journal.id]
            to_check_balance, number_to_check = to_check.get(journal, (0, 0))
            misc_balance, number_misc, misc_currencies = misc_totals.get(journal.default_account_id, (0, 0, currency))
            currency_consistent = misc_currencies == currency
            accessible = journal.company_id.id in journal.company_id._accessible_branches().ids
            nb_direct_payments, direct_payments_balance = direct_payment_balances[journal.id]
            drag_drop_settings = {
                'image': '/account/static/src/img/bank.svg' if journal.type in ('bank', 'credit') else '/web/static/img/rfq.svg',
                'text': _('Drop to import transactions'),
            }

            dashboard_data[journal.id].update({
                'number_to_check': number_to_check,
                'to_check_balance': currency.format(to_check_balance),
                'number_to_reconcile': number_to_reconcile.get(journal.id, 0),
                'account_balance': currency.format(journal.current_statement_balance + direct_payments_balance),
                'has_at_least_one_statement': bool(journal.last_statement_id),
                'nb_lines_bank_account_balance': (bool(journal.has_statement_lines) or bool(nb_direct_payments)) and accessible,
                'outstanding_pay_account_balance': currency.format(outstanding_pay_account_balance),
                'nb_lines_outstanding_pay_account_balance': has_outstanding,
                'last_balance': currency.format(journal.last_statement_id.balance_end_real),
                'last_statement_id': journal.last_statement_id.id,
                'bank_statements_source': journal.bank_statements_source,
                'is_sample_data': journal.has_statement_lines,
                'nb_misc_operations': number_misc,
                'misc_class': 'text-warning' if not currency_consistent else '',
                'misc_operations_balance': currency.format(misc_balance) if currency_consistent else None,
                'drag_drop_settings': drag_drop_settings,
            })

    def _graph_title_and_key(self):
        if self.type in ['sale', 'purchase']:
            return ['', _('Residual amount')]
        elif self.type == 'cash':
            return ['', _('Cash: Balance')]
        elif self.type == 'bank':
            return ['', _('Bank: Balance')]
        elif self.type == 'credit':
            return ['', _('Credit Card: Balance')]
        elif self.type == 'post_dated_cheque':
            return ['', _('PDC: Balance')]


    def _get_bank_cash_graph_data(self):
        """Computes the data used to display the graph for bank and cash journals in the accounting dashboard"""
        def build_graph_data(date, amount, currency):
            #display date in locale format
            name = format_date(date, 'd LLLL Y', locale=locale)
            short_name = format_date(date, 'd MMM', locale=locale)
            return {'x': short_name, 'y': currency.round(amount), 'name': name}

        today = datetime.today()
        last_month = today + timedelta(days=-30)
        locale = get_lang(self.env).code

        query = """
            SELECT move.journal_id,
                   move.date,
                   SUM(st_line.amount) AS amount
              FROM account_bank_statement_line st_line
              JOIN account_move move ON move.id = st_line.move_id
             WHERE move.journal_id = ANY(%s)
               AND move.date > %s
               AND move.date <= %s
               AND move.company_id = ANY(%s)
          GROUP BY move.date, move.journal_id
          ORDER BY move.date DESC
        """
        self.env.cr.execute(query, (self.ids, last_month, today, self.env.companies.ids))
        query_result = group_by_journal(self.env.cr.dictfetchall())

        result = {}
        for journal in self:
            graph_title, graph_key = journal._graph_title_and_key()
            # User may have read access on the journal but not on the company
            currency = journal.currency_id or self.env['res.currency'].browse(journal.company_id.sudo().currency_id.id)
            journal_result = query_result[journal.id]

            color = '#875A7B' if 'e' in version else '#7c7bad'
            is_sample_data = not journal_result and not journal.has_statement_lines

            data = []
            if is_sample_data:
                for i in range(30, 0, -5):
                    current_date = today + timedelta(days=-i)
                    data.append(build_graph_data(current_date, random.randint(-5, 15), currency))
                    graph_key = _('Sample data')
            else:
                last_balance = journal.current_statement_balance
                data.append(build_graph_data(today, last_balance, currency))
                date = today
                amount = last_balance
                #then we subtract the total amount of bank statement lines per day to get the previous points
                #(graph is drawn backward)
                for val in journal_result:
                    date = val['date']
                    if date.strftime(DF) != today.strftime(DF):  # make sure the last point in the graph is today
                        data[:0] = [build_graph_data(date, amount, currency)]
                    amount -= val['amount']

                # make sure the graph starts 1 month ago
                if date.strftime(DF) != last_month.strftime(DF):
                    data[:0] = [build_graph_data(last_month, amount, currency)]

            result[journal.id] = [{'values': data, 'title': graph_title, 'key': graph_key, 'area': True, 'color': color, 'is_sample_data': is_sample_data}]
        return result


    # def get_journal_dashboard_datas(self):
    #     currency = self.currency_id or self.company_id.currency_id
    #     number_to_reconcile = number_to_check = last_balance = 0
    #     has_at_least_one_statement = False
    #     bank_account_balance = nb_lines_bank_account_balance = 0
    #     outstanding_pay_account_balance = nb_lines_outstanding_pay_account_balance = 0
    #     title = ''
    #     number_draft = number_waiting = number_late = to_check_balance = 0
    #     sum_draft = sum_waiting = sum_late = 0.0
    #     ##################### Overrided #####################
    #     '''
    #     if self.type in ('bank', 'cash'):
    #     '''
    #     if self.type in ('bank', 'cash', 'post_dated_cheque'):
    #     ##################### ######### #####################
    #         last_statement = self._get_last_bank_statement(
    #             domain=[('state', 'in', ['posted', 'confirm'])])
    #         last_balance = last_statement.balance_end
    #         has_at_least_one_statement = bool(last_statement)
    #         bank_account_balance, nb_lines_bank_account_balance = self._get_journal_bank_account_balance(
    #             domain=[('move_id.state', '=', 'posted')])
    #         outstanding_pay_account_balance, nb_lines_outstanding_pay_account_balance = self._get_journal_outstanding_payments_account_balance(
    #             domain=[('move_id.state', '=', 'posted')])
    #
    #         self._cr.execute('''
    #             SELECT COUNT(st_line.id)
    #             FROM account_bank_statement_line st_line
    #             JOIN account_move st_line_move ON st_line_move.id = st_line.move_id
    #             JOIN account_bank_statement st ON st_line.statement_id = st.id
    #             WHERE st_line_move.journal_id IN %s
    #             --AND st.state = 'posted'
    #             AND NOT st_line.is_reconciled
    #         ''', [tuple(self.ids)])
    #         number_to_reconcile = self.env.cr.fetchone()[0]
    #
    #         to_check_ids = self.to_check_ids()
    #         number_to_check = len(to_check_ids)
    #         to_check_balance = sum([r.amount for r in to_check_ids])
    #     #TODO need to check if all invoices are in the same currency than the journal!!!!
    #     elif self.type in ['sale', 'purchase']:
    #         title = _('Bills to pay') if self.type == 'purchase' else _('Invoices owed to you')
    #         self.env['account.move'].flush(['amount_residual', 'currency_id', 'move_type', 'invoice_date', 'company_id', 'journal_id', 'date', 'state', 'payment_state'])
    #
    #         (query, query_args) = self._get_open_bills_to_pay_query()
    #         self.env.cr.execute(query, query_args)
    #         query_results_to_pay = self.env.cr.dictfetchall()
    #
    #         (query, query_args) = self._get_draft_bills_query()
    #         self.env.cr.execute(query, query_args)
    #         query_results_drafts = self.env.cr.dictfetchall()
    #
    #         today = fields.Date.context_today(self)
    #         query = '''
    #             SELECT
    #                 (CASE WHEN move_type IN ('out_refund', 'in_refund') THEN -1 ELSE 1 END) * amount_residual AS amount_total,
    #                 currency_id AS currency,
    #                 move_type,
    #                 invoice_date,
    #                 company_id
    #             FROM account_move move
    #             WHERE journal_id = %s
    #             AND date <= %s
    #             AND state = 'posted'
    #             AND payment_state in ('not_paid', 'partial')
    #             AND move_type IN ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt');
    #         '''
    #         self.env.cr.execute(query, (self.id, today))
    #         late_query_results = self.env.cr.dictfetchall()
    #         curr_cache = {}
    #         (number_waiting, sum_waiting) = self._count_results_and_sum_amounts(query_results_to_pay, currency, curr_cache=curr_cache)
    #         (number_draft, sum_draft) = self._count_results_and_sum_amounts(query_results_drafts, currency, curr_cache=curr_cache)
    #         (number_late, sum_late) = self._count_results_and_sum_amounts(late_query_results, currency, curr_cache=curr_cache)
    #         read = self.env['account.move'].read_group([('journal_id', '=', self.id), ('to_check', '=', True)], ['amount_total'], 'journal_id', lazy=False)
    #         if read:
    #             number_to_check = read[0]['__count']
    #             to_check_balance = read[0]['amount_total']
    #     elif self.type == 'general':
    #         read = self.env['account.move'].read_group([('journal_id', '=', self.id), ('to_check', '=', True)], ['amount_total'], 'journal_id', lazy=False)
    #         if read:
    #             number_to_check = read[0]['__count']
    #             to_check_balance = read[0]['amount_total']
    #
    #     is_sample_data = self.kanban_dashboard_graph and any(data.get('is_sample_data', False) for data in json.loads(self.kanban_dashboard_graph))
    #
    #     return {
    #         'number_to_check': number_to_check,
    #         'to_check_balance': formatLang(self.env, to_check_balance, currency_obj=currency),
    #         'number_to_reconcile': number_to_reconcile,
    #         'account_balance': formatLang(self.env, currency.round(bank_account_balance), currency_obj=currency),
    #         'has_at_least_one_statement': has_at_least_one_statement,
    #         'nb_lines_bank_account_balance': nb_lines_bank_account_balance,
    #         'outstanding_pay_account_balance': formatLang(self.env, currency.round(outstanding_pay_account_balance), currency_obj=currency),
    #         'nb_lines_outstanding_pay_account_balance': nb_lines_outstanding_pay_account_balance,
    #         'last_balance': formatLang(self.env, currency.round(last_balance) + 0.0, currency_obj=currency),
    #         'number_draft': number_draft,
    #         'number_waiting': number_waiting,
    #         'number_late': number_late,
    #         'sum_draft': formatLang(self.env, currency.round(sum_draft) + 0.0, currency_obj=currency),
    #         'sum_waiting': formatLang(self.env, currency.round(sum_waiting) + 0.0, currency_obj=currency),
    #         'sum_late': formatLang(self.env, currency.round(sum_late) + 0.0, currency_obj=currency),
    #         'currency_id': currency.id,
    #         'bank_statements_source': self.bank_statements_source,
    #         'title': title,
    #         'is_sample_data': is_sample_data,
    #         'company_count': len(self.env.companies)
    #     }

    def create_post_dated_cheque_statement(self):
        """return action to create a bank statements. This button should be called only on journals with type =='post_dated_cheque'"""
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_bank_statement_tree")
        action.update({
            'views': [[False, 'form']],
            'context': "{'default_journal_id': " + str(self.id) + "}",
        })
        return action