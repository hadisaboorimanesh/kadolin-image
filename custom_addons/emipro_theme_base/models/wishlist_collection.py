from odoo import api, fields, models


class WishlistCollection(models.Model):
    _name = "wishlist.collection"
    _description = "Wishlist Collection"

    def _default_partner(self):
        return self.env['res.users'].browse(self._uid).partner_id.id

    name = fields.Char(string="Collection", help="Name of Collection", required=True)
    partner_id = fields.Many2one(string="Customer", comodel_name="res.partner",
                                 help="User to which this collection belongs",
                                 default=_default_partner, required=True)
    product_line_ids = fields.One2many(string="Product Line", comodel_name="product.line",
                                       inverse_name="collection_id")

    def get_partner_collections(self, partner):
        """ Render the collections belongs to the given partner.
        """
        partner.ensure_one()
        return self.sudo().search([('partner_id', '=', partner.id)])

