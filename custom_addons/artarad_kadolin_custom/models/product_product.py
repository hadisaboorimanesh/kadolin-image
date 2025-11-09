# -*- coding: utf-8 -*-
from odoo import models, api, _,fields
from odoo.exceptions import ValidationError

class ProductProduct(models.Model):
    _inherit = "product.product"

    website_url = fields.Char(
        string="Website URL",
        help="The full URL to access the document through the website.",
    )

    @api.constrains("default_code", "active")
    def _akc_unique_default_code(self):
        for rec in self:
            code = (rec.default_code or "").strip()
            if not code:
                continue
            # یکتایی به ازای هر شرکت: (company_id, default_code)
            domain = [("default_code", "=", code)]
            if rec.company_id:
                domain.append(("company_id", "=", rec.company_id.id))
            else:
                # محصول گلوبال؛ فقط با محصولات گلوبال چک شود
                domain.append(("company_id", "=", False))
            if rec.id:
                domain.append(("id", "!=", rec.id))
            other = self.sudo().search(domain, limit=1)
            if other:
                comp_label = other.company_id.display_name or _("(بدون شرکت)")
                raise ValidationError(_(
                    "کد داخلی باید در سطح هر شرکت یکتا باشد. کد '%s' قبلاً برای '%s' در شرکت '%s' استفاده شده است."
                ) % (code, other.display_name, comp_label))
