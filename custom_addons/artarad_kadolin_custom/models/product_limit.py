# -*- coding: utf-8 -*-
from odoo import models, fields,api
import re
def _slugify(txt):
    txt = (txt or '').strip().lower()
    txt = re.sub(r'\s+', '-', txt)
    return re.sub(r'[^a-z0-9\-]+', '', txt)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    website_slug_en = fields.Char(
            string="Website Slug (English)",
            help="English-only slug used for website URLs.",
        )

    is_fake = fields.Boolean(string="غیر اصل",default = False)
    is_installment_snapp_pay = fields.Boolean(string="اقساطی اسنپ پی",default = True)

    free_shipping = fields.Boolean(compute="_compute_free_shipping",store=True)

    @api.depends("list_price")
    def _compute_free_shipping(self):
        for rec in self:
            rec.free_shipping =True
    # @api.depends('website_slug_en', 'name')
    # def _compute_website_url(self):
    #     # ابتدا رفتار پیش‌فرض را بسازد
    #     super()._compute_website_url()
    #     for product in self:
    #         if product.website_slug_en:
    #             slug_str = _slugify(product.website_slug_en)
    #             product.website_url = f"/shop/{slug_str}-{product.id}"