
import base64
import uuid

from odoo import api, fields, models
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.rating.models import rating_data
from odoo.tools.misc import file_open


class Rating(models.Model):
    _inherit = "rating.rating"

    is_internal = fields.Boolean('Visible Internally Only', default=False)

    @api.model_create_multi
    def create(self, values):
        res = super(Rating, self).create(values)
        for rec in res:
            rec.is_internal =False
        return res