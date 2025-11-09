from odoo import models, fields

class ResPartner(models.Model):
    _inherit = "res.partner"

    post_city_code = fields.Integer(
        "Post City Code",
        help="کد شهر مقصد (destcode) برای API پست. الزامی برای ارسال."
    )
    national_id = fields.Char("National ID", help="کد ملی گیرنده؛ اگر خالی باشد از vat استفاده می‌شود")