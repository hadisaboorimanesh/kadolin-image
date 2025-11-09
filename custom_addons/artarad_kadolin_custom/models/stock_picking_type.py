from odoo import fields, models

class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    pack_no_reserve = fields.Boolean(
        string="Never Reserve on This Operation",
        default=False,
    )

    type_code = fields.Selection([('pick','Pick'),('pack','Pack'),('deliver','Deliver')])