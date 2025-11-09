from odoo import models, fields

class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    # فعال شدن این carrier
    delivery_type = fields.Selection(selection_add=[("post", "Post (Iran Post)")],ondelete={'post': 'set default'},)

    # تنظیمات اتصال
    post_base_url = fields.Char(
        string="Post Base URL",
        default="http://poffice.post.ir/restservice/api",
        help="e.g. http://poffice.post.ir/restservice/api",
    )
    post_contract_code = fields.Char("Contract Code")
    post_username = fields.Char("Username")
    post_password = fields.Char("Password")

    # پارامترهای ثابت/پیش‌فرض درخواست
    post_postnodecode = fields.Char("Post Node Code", help="postnodecode (کد رهگیری/گره پستی)")
    post_typecode = fields.Integer("Type Code", default=11, help="نوع مرسوله: 11=پیشتاز ...")
    post_servicetype = fields.Integer("Service Type", default=1, help="1=پیشتاز, 2=سفارشی, 3=ویژه")
    post_parceltype = fields.Integer("Parcel Type", default=2, help="2=بسته پیشتاز ...")

    post_postalcostcategoryid = fields.Integer("Postal Cost Category", default=1)
    post_postalcosttypeflag = fields.Selection([
        ("F", "F"),
        ("A", "A"), ("R", "R"), ("C", "C"), ("V", "V"),
        ("S", "S"), ("I", "I"), ("N", "N"), ("P", "P"), ("L", "L"),
    ], string="Postal Cost Type Flag", default="F")

    post_insurancetype = fields.Integer("Insurance Type", default=1, help="1=عادی, 3=اوراق, 5=سایر")
    post_insuranceamount = fields.Integer("Insurance Amount (Rials)", default=0)

    post_spsdestinationtype = fields.Integer("SPS Destination Type", default=0)
    post_spsreceivertimetype = fields.Integer("SPS Receiver Time Type", default=0)
    post_spsparceltype = fields.Integer("SPS Parcel Type", default=0)
    post_tlsservicetype = fields.Integer("TLS Service Type", default=0, help="0=اداری,1=بعداداری,2=شبانه")

    post_tworeceiptant = fields.Boolean("Two-Receipt", default=False)
    post_electroreceiptant = fields.Boolean("Electronic Receipt", default=False)
    post_iscot = fields.Boolean("Cash On Destination (iscot)", default=False)
    post_smsservice = fields.Boolean("SMS Service", default=False)
    post_isnonstandard = fields.Boolean("Non-standard (Jof)", default=True)

    post_sendplacetype = fields.Integer("Send Place Type", default=2, help="0/1/2/3 مطابق جدول حق مقر")
    post_contractorportion = fields.Integer("Contractor Portion", default=0, help="حق‌السهم طرف قرارداد (ریال)")

    # مبدأ و فرستنده
    post_source_city_code = fields.Integer("Source City Code", help="کد شهر مبدأ (sourcecode)")
    post_sender_name = fields.Char("Sender Name", help="نام فرستنده؛ اگر خالی باشد از شرکت استفاده می‌شود")
    post_sender_postalcode = fields.Char("Sender Postal Code")
    post_sender_national_id = fields.Char("Sender National ID")
    post_sender_mobile = fields.Char("Sender Mobile")
    post_sender_address = fields.Text("Sender Address")

    post_contents = fields.Char("Contents", help="Contetnts در مستند")
    post_boxsize = fields.Integer("Box Size", default=6)