from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError
from odoo.tools import config, float_compare


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        base_location = self.move_id.picking_id.location_id or self.location_id
        quants = self.env['stock.quant'].sudo().search([
            ('product_id', '=', self.product_id.id),
            ('lot_id', '=', self.lot_id.id),
            ('quantity', '!=', 0),
            ('location_id.usage', 'in', ('internal', 'transit', 'customer')),
            ('location_id', 'not any', [('location_id', 'child_of', base_location.id)])
        ])

        if quants:
               raise UserError(_('Unavailable Serial numbers. Please correct the serial numbers encoded'))



class StockMove(models.Model):
    _inherit = "stock.move"

    @api.onchange('lot_ids')
    def _onchange_lot_ids(self):
        quantity = sum(
            ml.quantity_product_uom for ml in self.move_line_ids.filtered(lambda ml: not ml.lot_id and ml.lot_name))
        quantity += self.product_id.uom_id._compute_quantity(len(self.lot_ids), self.product_uom)
        self.update({'quantity': quantity})

        base_location = self.picking_id.location_id or self.location_id
        quants = self.env['stock.quant'].sudo().search([
            ('product_id', '=', self.product_id.id),
            ('lot_id', 'in', self.lot_ids.ids),
            ('quantity', '!=', 0),
            ('location_id.usage', 'in', ('internal', 'transit', 'customer')),
            ('location_id', 'not any', [('location_id', 'child_of', base_location.id)])
        ])

        if quants:
            sn_to_location = ""
            for quant in quants:
                sn_to_location += _("\n(%(serial_number)s) exists in location %(location)s",
                                    serial_number=quant.lot_id.display_name, location=quant.location_id.display_name)
            raise UserError(_('Unavailable Serial numbers. Please correct the serial numbers encoded: %s',
                    sn_to_location))
            return {
                'warning': {'title': _('Warning'), 'message': _(
                    'Unavailable Serial numbers. Please correct the serial numbers encoded: %(serial_numbers_to_locations)s',
                    serial_numbers_to_locations=sn_to_location)}
            }

class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.constrains("product_id", "quantity")
    def check_negative_qty(self):
        p = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        check_negative_qty = (
            config["test_enable"] and self.env.context.get("test_stock_no_negative")
        ) or not config["test_enable"]
        if not check_negative_qty:
            return

        for quant in self:
            disallowed_by_product = (
                not quant.product_id.allow_negative_stock
                and not quant.product_id.categ_id.allow_negative_stock
            )
            disallowed_by_location = not quant.location_id.allow_negative_stock
            if (
                float_compare(quant.quantity, 0, precision_digits=p) == -1
                and quant.product_id.type == "product"
                and quant.location_id.usage in ["internal", "transit"]
                and disallowed_by_product
                and disallowed_by_location
            ):
                msg_add = ""
                if quant.lot_id:
                    msg_add = _(" lot {}").format(quant.lot_id.name_get()[0][1])
                raise exceptions.ValidationError(
                    _(
                        "You cannot validate this stock operation because the "
                        "stock level of the product '{name}'{name_lot} would "
                        "become negative "
                        "({q_quantity}) on the stock location '{complete_name}' "
                        "and negative stock is "
                        "not allowed for this product and/or location."
                    ).format(
                        name=quant.product_id.display_name,
                        name_lot=msg_add,
                        q_quantity=quant.quantity,
                        complete_name=quant.location_id.complete_name,
                    )
                )
