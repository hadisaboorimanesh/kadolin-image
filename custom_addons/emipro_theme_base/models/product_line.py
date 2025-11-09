from odoo import api, fields, models


class ProductLine(models.Model):
    _name = "product.line"
    _description = "Product Line"

    collection_id = fields.Many2one(comodel_name="wishlist.collection",
                                    help="Collection in which this product line belongs",
                                    string="Wishlist Collection", required=True)
    product_id = fields.Many2one(comodel_name="product.product", string="Product", required=True)
    quantity = fields.Integer(string="Quantity", help="Quantity of Product", default=1)
