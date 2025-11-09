# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ProductRibbonEPT(models.Model):
    """
        This model is used to store custom product ribbon style on the product.
    """
    _inherit = "product.ribbon"
    html = fields.Html(string='Ribbon html', translate=True, sanitize=False, default='')
    products_count = fields.Integer('Product Count', compute='_compute_products_count',
                                    help='Number of product counts that configured to label')
    sequence = fields.Integer('Sequence', index=True, default=10)
    product_ids = fields.One2many('product.template', 'website_ribbon_id', 'Products')
    position = fields.Selection(selection_add=[('o_product_label_style_1_left', 'Vega Tag Left'),
                                               ('o_product_label_style_1_right', 'Vega Tag Right'),
                                               ('o_product_label_style_2_left', 'Vega Square Shadow Left'),
                                               ('o_product_label_style_2_right', 'Vega Square Shadow Right'),
                                               ('o_product_label_style_3_left', 'Vega Edge Left'),
                                               ('o_product_label_style_3_right', 'Vega Edge Right'),
                                               ('o_product_label_style_4_left', 'Vega Round Left'),
                                               ('o_product_label_style_4_right', 'Vega Round '
                                                                                 'Right')],
                                default='left',
                                ondelete={
                                    "o_product_label_style_1_left": "set default",
                                    "o_product_label_style_1_right": "set default",
                                    "o_product_label_style_2_left": "set default",
                                    "o_product_label_style_2_right": "set default",
                                    "o_product_label_style_3_left": "set default",
                                    "o_product_label_style_3_right": "set default",
                                    "o_product_label_style_4_left": "set default",
                                    "o_product_label_style_4_right": "set default",
                                },)
    @api.depends('product_ids')
    def _compute_products_count(self):
        for label in self:
            label.products_count = len(label.product_ids)

    def set_label_wizard(self):
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'product.label.config',
            'name': "Product Configuration",
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_label_id': self.id},
        }
        return action

    def clear_all_products(self):
        self.product_ids = None

    def _get_position_class(self):
        position_map = {
            'left': 'o_ribbon_left',
            'o_product_label_style_1_left': 'o_product_label_style_1_left',
            'o_product_label_style_1_right': 'o_product_label_style_1_right',
            'o_product_label_style_2_left': 'o_product_label_style_2_left',
            'o_product_label_style_2_right': 'o_product_label_style_2_right',
            'o_product_label_style_3_left': 'o_product_label_style_3_left',
            'o_product_label_style_3_right': 'o_product_label_style_3_right',
            'o_product_label_style_4_left': 'o_product_label_style_4_left',
            'o_product_label_style_4_right': 'o_product_label_style_4_right'
        }
        return position_map.get(self.position, 'o_ribbon_right')





