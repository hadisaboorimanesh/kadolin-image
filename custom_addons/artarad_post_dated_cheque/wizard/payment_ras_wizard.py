from odoo import models, fields, api
from datetime import timedelta

class PaymentRASWizard(models.TransientModel):
    _name = 'payment.ras.wizard'
    _description = 'Payment RAS Result'

    ras_date = fields.Date(string="تاریخ راس", readonly=True)
    base_date = fields.Date(string="تاریخ مبنا", default=fields.Date.context_today)
    payment_ids = fields.Many2many('account.payment', string="پرداخت‌ها",)
    diff_days = fields.Integer(string="تعداد روز",compute="compute_diff_days")

    @api.depends("base_date","ras_date")
    def compute_diff_days(self):
        for rec in self:
            rec.diff_days = (rec.ras_date- rec.base_date).days

    @api.onchange('base_date', 'payment_ids')
    def _onchange_compute_ras(self):
        if not self.payment_ids or not self.base_date:
            self.ras_date = False
            return

        total_amount = 0
        ras_days_total = 0

        for line in self.payment_ids:
            if line.date and line.amount:
                delta = ((line.cheque_date or line.cheque_date) - self.base_date).days
                ras_days_total += line.amount * delta
                total_amount += line.amount

        if total_amount:
            final_days = int(ras_days_total / total_amount)
            self.ras_date = self.base_date + timedelta(days=final_days)
        else:
            self.ras_date = False

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        payments = self.env['account.payment'].browse(active_ids)

        base_date = fields.Date.context_today(self)  # تاریخ مبنا را اینجا می‌گیریم
        ras_days = 0
        total_amount = 0

        for p in payments:
            if p.date and p.amount:
                delta_days = (p.date - base_date).days
                ras_days += p.amount * delta_days
                total_amount += p.amount

        if total_amount:
            final_days = int(ras_days / total_amount)
            ras_date = base_date + timedelta(days=final_days)
        else:
            ras_date = False

        result.update({
            'payment_ids': [(6, 0, payments.ids)],
            'ras_date': ras_date,
            'base_date': base_date,
        })

        return result
