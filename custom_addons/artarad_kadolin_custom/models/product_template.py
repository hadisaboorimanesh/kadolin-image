# -*- coding: utf-8 -*-
from odoo import models, fields,api
import re

class LoyaltyRule(models.Model):
    _inherit = 'loyalty.rule'


    reward_point_amount = fields.Float(default=1, string="Reward",digits=(12, 6))


class ProductTemplate(models.Model):
    _inherit = "product.template"

    seo_name = fields.Char(
            string="Website Slug (English)",
            help="English-only slug used for website URLs.",
        )

    is_fake = fields.Boolean(string="غیر اصل",default = False)
    is_installment_snapp_pay = fields.Boolean(string="اقساطی اسنپ پی",default = True)
    free_shipping = fields.Boolean(compute="_compute_free_shipping",store=True)
    backorder_lead_days = fields.Float(
        string="Backorder Lead Time (days)",
        help="Lead time to promise when the product is not in stock. If empty, company default is used.",
        default=0.0,
    )





    @api.depends("list_price")
    def _compute_free_shipping(self):
        for rec in self:
            rec.free_shipping =True