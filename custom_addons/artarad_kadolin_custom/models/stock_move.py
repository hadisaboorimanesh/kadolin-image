from odoo import api, models,_
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = "stock.move"

    # به‌جای generate_lot_names(...) این را بگذار
    def _sequence_lot_names(self, company_id, n):
        # سکانس درست را برای همان شرکت پیدا کن و با next_by_id در حلقه بخوان
        seq = self.env['ir.sequence'].sudo().search(
            [('code', '=', 'stock.lot.serial'),
             ('company_id', 'in', [company_id or self.env.company.id, False])],
            limit=1, order='company_id desc'
        )
        if not seq:
            # اگر رکورد سکانس پیدا نشد (نادر)، همان next_by_code هم کار می‌کند؛
            # ولی بهتر است یک UserError بدهی تا کانفیگ را درست کنی.
            raise UserError(_("No 'stock.lot.serial' sequence configured."))

        return [{'lot_name': seq.next_by_id()} for _ in range(n)]

    @api.model
    def action_generate_lot_line_vals(self, context, mode, first_lot, count, lot_text):
        """Force using Odoo's default lot sequence (ignore user pattern & import text)."""
        if not context.get('default_product_id'):
            raise UserError(_("No product found to generate Serials/Lots for."))
        assert mode in ('generate', 'import')

        default_vals = {}

        def generate_lot_qty(quantity, qty_per_lot):
            if qty_per_lot <= 0:
                raise UserError(_("The quantity per lot should always be a positive value."))
            line_count = int(quantity // qty_per_lot)
            leftover = quantity % qty_per_lot
            qty_array = [qty_per_lot] * line_count
            if leftover:
                qty_array.append(leftover)
            return qty_array

        def remove_prefix(text, prefix):
            if text.startswith(prefix):
                return text[len(prefix):]
            return text

        # collect default_* from context
        for key in context:
            if key.startswith('default_'):
                default_vals[remove_prefix(key, 'default_')] = context[key]

        # quantities
        if default_vals.get('tracking') == 'lot' and mode == 'generate':
            lot_qties = generate_lot_qty(default_vals['quantity'], count)
        else:
            lot_qties = [1] * count

        # ⬇️ تغییر اصلی: همیشه از سکونس پیش‌فرض اودو استفاده کن
        # با first_lot=False => اودو از ir.sequence خودش سریال می‌سازه
        lot_names = self._sequence_lot_names(default_vals.get('company_id'), len(lot_qties))
        vals_list = []
        for lot, qty in zip(lot_names, lot_qties):
            if not lot.get('quantity'):
                lot['quantity'] = qty
            loc_dest = self.env['stock.location'].browse(default_vals['location_dest_id'])
            product = self.env['product.product'].browse(default_vals['product_id'])
            loc_dest = loc_dest._get_putaway_strategy(product, lot['quantity'])
            vals_list.append({
                **default_vals,
                **lot,
                'location_dest_id': loc_dest.id,
                'product_uom_id': product.uom_id.id,
            })

        if default_vals.get('picking_type_id'):
            picking_type = self.env['stock.picking.type'].browse(default_vals['picking_type_id'])
            if picking_type.use_existing_lots:
                self._create_lot_ids_from_move_line_vals(
                    vals_list, default_vals['product_id'], default_vals['company_id']
                )

        # format many2one values for webclient
        for values in vals_list:
            for key, value in values.items():
                if key in self.env['stock.move.line'] and isinstance(self.env['stock.move.line'][key], models.Model):
                    values[key] = {
                        'id': value,
                        'display_name': self.env['stock.move.line'][key].browse(value).display_name
                    }
        return vals_list

    def _action_assign(self):
        # moves داخل پیکینگ‌هایی که نباید رزرو شوند
        blocked = self.filtered(lambda m: m.picking_id and m.picking_id.picking_type_id.pack_no_reserve)
        allowed = self - blocked

        # همیشه با رکوردست خالی شروع کن
        result = self.env['stock.move']
        if allowed:
           result = super(StockMove, allowed)._action_assign()
        if blocked:
           blocked._do_unreserve()
        return result

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def write(self, vals):
        res = super().write(vals)

        # فقط وقتی prefill خاموش است و در حوالهٔ PACK هستیم:
        def _prefill_off(env):
            val = env['ir.config_parameter'].sudo().get_param('artarad.pack_prefill_enabled', '0')
            return val != '1'

        if _prefill_off(self.env):
            lines = self.filtered(lambda l: l.picking_id and l.picking_id._is_pack() and not l.result_package_id)
            for ml in lines:
                # اگر qty_done تازه مقدار گرفته یا قبلاً >0 است، مقصد را روی سبد هدف بگذار
                qty_done_now = ('qty_done' in vals and vals['qty_done']) or ml.qty_done
                if qty_done_now and qty_done_now > 0:
                    target_pkg = ml.picking_id.akc_target_package_id
                    if target_pkg and target_pkg.akc_reusable and target_pkg.akc_in_use:
                        ml.result_package_id = target_pkg.id

        return res