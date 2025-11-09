from odoo import models,fields,api,_
from odoo.api import readonly
from odoo.exceptions import UserError
from random import choices

from datetime import date, timedelta

class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    akc_reusable = fields.Boolean(string="Reusable (AKC)", default=False)
    akc_in_use = fields.Boolean(string="In Use (AKC)", default=False, help="Temporarily reserved for a PACK picking.")
    new_location_id = fields.Many2one('stock.location', string='Assigned Location', help='Home location for this reusable package')

    def akc_mark_free(self):

        for p in self:
            Quant = self.env['stock.quant'].sudo()
            quants = Quant.search([('package_id', '=', p.id)])
            if quants:
                quants.write({'package_id': False})
            p.write({'akc_in_use': False})
            p.unpack()

    def write(self, vals):
        res = super().write(vals)

        reusable = self.filtered(lambda p: p.akc_reusable)
        if not reusable:
            return res
        freed = reusable
        if 'akc_in_use' in vals and vals['akc_in_use'] is False:
            freed = reusable.filtered(lambda p: not p.akc_in_use)

        if not freed:
            return res

        Picking = self.env['stock.picking'].sudo()
        Quant = self.env['stock.quant'].sudo()
        for pkg in freed:
            if Quant.search_count([('package_id', '=', pkg.id)]) > 0:
                continue

            candidates = Picking.search([
                ('picking_type_id.code', '=', 'internal'),
                ('state', 'in', ('assigned', 'confirmed', 'waiting')),
            ], order='priority desc, scheduled_date asc, id asc', limit=50)

            candidates = candidates.filtered(lambda p:
                                             p.picking_type_id and p.picking_type_id.type_code =='pack'
                                             and not any(p.move_line_ids.mapped('result_package_id'))
                                             )
            if not candidates:
                continue

            target = candidates[0]
            target.akc_assign_specific_package(pkg)

        return res

class StockPicking(models.Model):
    _inherit = "stock.picking"

    invoice_id = fields.Many2one('account.move', copy=False)
    pakage_id = fields.Many2one("stock.quant.package",compute="_compute_pakage_id",store=True)

    akc_target_package_id = fields.Many2one(
        'stock.quant.package',
        string="Target Package (AKC)",
        help="When packing via barcode, scanned lines will be put in this package."
    )

    delivery_slot = fields.Selection([
        ('morning', '9 تا 15'),
        ('evening', '15 تا 21'),
    ], string="Delivery Slot")



    def _prefill_enabled(self):
        """Feature flag: اگر True باشد رفتار قبلی (prefill) حفظ می‌شود."""
        val = self.env['ir.config_parameter'].sudo().get_param('artarad.pack_prefill_enabled', '1')
        return val == '1'

    @api.depends("move_line_ids.result_package_id")
    def _compute_pakage_id(self):
        for rec in self:
            rec.pakage_id=rec.move_line_ids[0].result_package_id.id if rec.move_line_ids else False

    def action_cancel(self):
        res = super().action_cancel()
        packs_to_free = self._is_pack()
        if packs_to_free:
            Quant = self.env['stock.quant'].sudo()
            dest_pkgs = packs_to_free.mapped('move_line_ids.result_package_id').filtered(lambda p: p and p.akc_reusable)
            for pkg in dest_pkgs:
                quants = Quant.search([('package_id', '=', pkg.id)])
                if quants:
                    quants.write({'package_id': False})
                pkg.write({'akc_in_use': False})
                pkg.akc_mark_free()
                pkg.unpack()
        return res

    # ---------- Helpers ----------
    def _is_pick(self):
        return self.filtered(
            lambda p: p.picking_type_id and p.picking_type_id.type_code =='pick')

    def _is_pack(self):
        return self.filtered(
            lambda p: p.picking_type_id
                      and p.picking_type_id.type_code =='pack'
        )

    def _akc_get_free_reusable_package(self):

        if not self:
            return False
        picking = self if len(self) == 1 else self[0]
        Package = picking.env['stock.quant.package'].sudo()
        domain = [('akc_reusable', '=', True), ('akc_in_use', '=', False)]
        pkg = False
        if picking.location_dest_id:
            domain_loc = list(domain) + [('new_location_id', '=', picking.location_id.id)]
            pkg = Package.search(domain_loc, order='name asc', limit=1)
        if not pkg:
            domain_loc = list(domain) + [('new_location_id', '=', picking.move_line_ids[0].location_id.id)]
            pkg = Package.search(domain_loc, order='name asc', limit=1)
        if pkg:
            pkg.write({'akc_in_use': True})
        return pkg

    # def _akc_auto_put_in_pack_now(self):
    #     """روی حوالهٔ PACK: همهٔ لاین‌ها را در یکی از پکیج‌های خالی قرار بده."""
    #     for picking in self._is_pack():
    #         if picking.state in ('done', 'cancel'):
    #             continue
    #         # اگر قبلاً مقصدی ست شده، دخالت نکن
    #         if any(picking.move_line_ids.mapped('result_package_id')):
    #             continue
    #
    #         pkg = self._akc_get_free_reusable_package()
    #         if not pkg:
    #             continue
    #
    #         mls = picking.move_line_ids
    #
    #         # اگر move line نداریم، از روی move ها بسازیم
    #         if not mls and picking.move_ids_without_package:
    #             for mv in picking.move_ids_without_package:
    #                 if not mv.move_line_ids:
    #                     mv._action_assign()  # رزرو در صورت نیاز
    #                     self.env['stock.move.line'].create({
    #                         'move_id': mv.id,
    #                         'picking_id': picking.id,
    #                         'product_id': mv.product_id.id,
    #                         'location_id': mv.location_id.id,
    #                         'location_dest_id': mv.location_dest_id.id,
    #                         'product_uom_id': mv.product_uom.id,
    #                         'qty_done': mv.product_uom_qty or 0.0,
    #                     })
    #             mls = picking.move_line_ids
    #
    #         # qty_done را (اگر صفر) پر کن و مقصد را روی پکیج انتخابی بگذار
    #         for ml in mls:
    #             if not ml.qty_done or ml.qty_done <= 0.0:
    #                 qty_needed = ml.quantity or ml.move_id.product_uom_qty or 0.0
    #                 if qty_needed > 0:
    #                     ml.qty_done = qty_needed
    #             ml.result_package_id = pkg.id
    def _akc_auto_put_in_pack_now(self):
        """
        اگر prefill روشن باشد: همان رفتار قبلی (ساخت/پرکردن موولاین و ...).
        اگر خاموش باشد: سبد را رزرو می‌کنیم و روی خطوطِ موجود می‌گذاریم؛
        اگر خطی وجود نداشت، برای هر موو یک خط با qty_done=0 می‌سازیم و result_package_id را همان‌جا ست می‌کنیم.
        (lot_id را نمی‌زنیم تا بارکد سریال‌ها را تا لحظهٔ اسکن نشان ندهد.)
        """
        for picking in self._is_pack():
            if picking.state in ('done', 'cancel'):
                continue
            # اگر قبلاً مقصدی ست شده، دخالت نکن
            if any(picking.move_line_ids.mapped('result_package_id')):
                continue

            pkg = picking._akc_get_free_reusable_package()
            if not pkg:
                continue
            pkg.unpack()

            if self._prefill_enabled():
                # --- رفتار قبلی ---
                mls = picking.move_line_ids
                if not mls and picking.move_ids_without_package:
                    for mv in picking.move_ids_without_package:
                        if not mv.move_line_ids:
                            mv._action_assign()
                            self.env['stock.move.line'].create({
                                'move_id': mv.id,
                                'picking_id': picking.id,
                                'product_id': mv.product_id.id,
                                'location_id': mv.location_id.id,
                                'location_dest_id': mv.location_dest_id.id,
                                'product_uom_id': mv.product_uom.id,
                                'qty_done': mv.product_uom_qty or 0.0,
                            })
                    mls = picking.move_line_ids

                for ml in mls:
                    if not ml.qty_done or ml.qty_done <= 0.0:
                        qty_needed = ml.quantity or ml.move_id.product_uom_qty or 0.0
                        if qty_needed > 0:
                            ml.qty_done = qty_needed
                    ml.result_package_id = pkg.id
            else:
                # --- حالت جدید: سبد را همین الان روی خطوط بگذار، بدون پرکردن qty_done/lot_id ---
                mls = picking.move_line_ids
                # اگر موولاین نداریم، باید بسازیم (اما qty_done=0 و بدون lot_id)
                if not mls and picking.move_ids_without_package:
                    for mv in picking.move_ids_without_package:
                        if not mv.move_line_ids:
                            try:
                                mv._action_assign()
                            except Exception:
                                pass
                            self.env['stock.move.line'].create({
                                'move_id': mv.id,
                                'picking_id': picking.id,
                                'product_id': mv.product_id.id,
                                'location_id': mv.location_id.id,
                                'location_dest_id': mv.location_dest_id.id,
                                'product_uom_id': mv.product_uom.id,
                                'qty_done': 0.0,  # 👈 صفر می‌ماند
                                # lot_id عمداً ست نمی‌شود
                                'result_package_id': pkg.id,  # 👈 سبد از همین الان روی خط
                            })
                    mls = picking.move_line_ids

                # اگر خط داشتیم، فقط مقصد را روی سبد بگذاریم؛ qty_done/lot_id دست‌نخورده
                if mls:
                    mls.filtered(lambda ml: not ml.result_package_id).write({'result_package_id': pkg.id})

                # برای سازگاری با سایر هوک‌ها، سبد هدف هم نگه داشته می‌شود
                picking.akc_target_package_id = pkg.id

    def akc_assign_specific_package(self, package):
        """
        اگر prefill روشن است، مثل قبل qty_done را پر می‌کند و همه خطوط را در package می‌اندازد.
        اگر خاموش است، qty_done/lot_id را دست نمی‌زنیم؛
        ولی مطمئن می‌شویم همهٔ خطوط این حواله result_package_id=package داشته باشند.
        اگر خطی نبود، برای هر موو یک خط با qty_done=0 ساخته و package ست می‌شود.
        """
        self.ensure_one()
        # New: ensure package location matches picking destination (if both defined)
        if (package.new_location_id and self.location_id and
                ( package.new_location_id.id != self.location_id.id or package.new_location_id.id != self.move_line_ids[0].location_id.id)):
            return False
        if self.state in ('done', 'cancel'):
            return False
        if not package or not package.akc_reusable or package.akc_in_use:
            return False

        package.sudo().write({'akc_in_use': True})

        if self._prefill_enabled():
            # --- رفتار قبلی ---
            mls = self.move_line_ids
            if not mls and self.move_ids_without_package:
                for mv in self.move_ids_without_package:
                    if not mv.move_line_ids:
                        try:
                            mv._action_assign()
                        except Exception:
                            pass
                        if not mv.move_line_ids:
                            self.env['stock.move.line'].create({
                                'move_id': mv.id,
                                'picking_id': self.id,
                                'product_id': mv.product_id.id,
                                'location_id': mv.location_id.id,
                                'location_dest_id': mv.location_dest_id.id,
                                'product_uom_id': mv.product_uom.id,
                                'qty_done': mv.product_uom_qty or 0.0,
                            })
            mls = self.move_line_ids
            for ml in mls:
                if not ml.qty_done or ml.qty_done <= 0.0:
                    qty_needed = getattr(ml, 'reserved_uom_qty',
                                         0.0) or ml.product_uom_qty or ml.move_id.product_uom_qty or 0.0
                    if qty_needed > 0:
                        ml.qty_done = qty_needed
                ml.result_package_id = package.id
            return True
        else:
            # --- حالت جدید: سبد را روی خطوط بگذار، بدون qty_done/lot_id ---
            mls = self.move_line_ids
            if not mls and self.move_ids_without_package:
                for mv in self.move_ids_without_package:
                    if not mv.move_line_ids:
                        try:
                            mv._action_assign()
                        except Exception:
                            pass
                        self.env['stock.move.line'].create({
                            'move_id': mv.id,
                            'picking_id': self.id,
                            'product_id': mv.product_id.id,
                            'location_id': mv.location_id.id,
                            'location_dest_id': mv.location_dest_id.id,
                            'product_uom_id': mv.product_uom.id,
                            'qty_done': 0.0,  # 👈 صفر
                            'result_package_id': package.id,  # 👈 سبد روی خط
                        })
                mls = self.move_line_ids

            if mls:
                mls.filtered(lambda ml: not ml.result_package_id).write({'result_package_id': package.id})

            # برای ادامهٔ اسکن‌ها، سبد هدف هم نگه‌داری شود
            self.akc_target_package_id = package.id
            return True

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        recs._assign_pack_carrier()
        if recs.sale_id and recs.sale_id.delivery_slot:
            recs.delivery_slot = recs.sale_id.delivery_slot
        recs._is_pack().filtered(lambda p: p.state in ('assigned', 'confirmed', 'waiting'))._akc_auto_put_in_pack_now()
        return recs

    def action_assign(self):
        # قبل و بعد از assign بررسی می‌کنیم
        packs_before = self._is_pack()
        res = super().action_assign()
        packs_after = packs_before.filtered(lambda p: p.state == 'assigned')
        if packs_after:
            packs_after._akc_auto_put_in_pack_now()
        return res

    def button_validate(self):
        # قبل از سوپر، تشخیص بده کدام‌ها PICK هستند
        picks_before = self.filtered(
            lambda p: p.picking_type_id
                      and p.picking_type_id.type_code =='pick'
                      and p.state not in ('done', 'cancel')
        )
        packs_before = self.filtered(
            lambda p: p.picking_type_id
                      and p.picking_type_id.type_code =='pack'
                      and p.state not in ('done', 'cancel')
        )
        res = super().button_validate()

        # 🔹 پس از دانِ PICK: PACKهای مرتبط را پیدا کن و همان‌جا پکیج بده
        if picks_before:
            for pick in picks_before:
                packs = self.search([
                    ('group_id', '=', pick.group_id.id),
                    ('state', 'in', ('assigned', 'confirmed', 'waiting')),
                    ('picking_type_id.type_code', '=', 'pack'),
                ])
                packs._akc_auto_put_in_pack_now()

        # 🔹 پس از دان PACK: بسته‌ها را خالی و آزاد کن
        packs_to_free = self._is_pack().filtered(lambda p: p.state not in ('done', 'cancel'))
        if packs_to_free:
            Quant = self.env['stock.quant'].sudo()
            dest_pkgs = packs_to_free.mapped('move_line_ids.result_package_id').filtered(lambda p: p and p.akc_reusable)
            for pkg in dest_pkgs:
                quants = Quant.search([('package_id', '=', pkg.id)])
                if quants:
                    quants.write({'package_id': False})
                pkg.write({'akc_in_use': False})
                pkg.akc_mark_free()
                pkg.unpack()

        packs_done_now = packs_before.filtered(lambda p: p.state == 'done')
        if packs_done_now:
            # پکیج‌هایی که روی این حواله‌ها استفاده شدند (فقط reusable)
            used_pkgs = packs_done_now.mapped('move_line_ids.result_package_id').filtered(
                lambda p: p and p.akc_reusable)
            if used_pkgs:
                self._akc_empty_packages(used_pkgs)

        if res == True:
            for rec in self:
                if rec.sale_id:
                    if rec.picking_type_id.code == 'outgoing':  # Normal delivery
                        invoice = rec.sale_id._create_invoices()
                        invoice.action_post()
                        rec.invoice_id = invoice.id

                    elif rec.picking_type_id.code == 'incoming':  # Return picking (Refund Invoice)
                        adv_wiz = self.env['sale.advance.payment.inv'].with_context(
                            active_ids=[rec.sale_id.id]).create(
                            {
                                'advance_payment_method': 'delivered',
                            })
                        act = adv_wiz.with_context().create_invoices()
                        invoice = self.env['account.move'].browse(act['res_id'])
                        invoice.action_post()
                        rec.invoice_id = invoice.id
        return res

    def _akc_empty_packages(self, packages):
        """Detach all quants from given reusable packages and mark them free (Odoo 18-safe)."""
        Quant = self.env['stock.quant'].sudo()
        has_parent = 'parent_id' in self.env['stock.quant.package']._fields  # برای سازگاری نسخه‌ها

        for pkg in packages:
            # همه‌ی کوانت‌های داخل این پکیج را جدا کن
            quants = Quant.search([('package_id', '=', pkg.id)])
            if quants:
                quants.write({'package_id': False})

            # اگر نسخه‌ای از اودو parent_id داشت، جدا کن (در v18 معمولاً نیست)
            if has_parent and pkg.parent_id:
                pkg.parent_id = False

            # پکیج را آزاد کن تا دوباره مصرف شود
            pkg.write({'akc_in_use': False})
            pkg.akc_mark_free()
            pkg.unpack()

    # def akc_assign_specific_package(self, package):
    #     """تمام موولاین‌های PACK را در این سبد قرار بده (در صورت نیاز موولاین بساز؛ qty_done را پر کن)."""
    #     self.ensure_one()
    #     if self.state in ('done', 'cancel'):
    #         return False
    #     if not package or not package.akc_reusable or package.akc_in_use:
    #         return False
    #
    #     # جلوگیری از ریس: همین الآن سبد را در حال استفاده علامت بزن
    #     package.sudo().write({'akc_in_use': True})
    #
    #     # اگر موولاین نداریم، بساز
    #     mls = self.move_line_ids
    #     if not mls and self.move_ids_without_package:
    #         for mv in self.move_ids_without_package:
    #             if not mv.move_line_ids:
    #                 try:
    #                     mv._action_assign()
    #                 except Exception:
    #                     pass
    #                 if not mv.move_line_ids:
    #                     self.env['stock.move.line'].create({
    #                         'move_id': mv.id,
    #                         'picking_id': self.id,
    #                         'product_id': mv.product_id.id,
    #                         'location_id': mv.location_id.id,
    #                         'location_dest_id': mv.location_dest_id.id,
    #                         'product_uom_id': mv.product_uom.id,
    #                         'qty_done': mv.product_uom_qty or 0.0,
    #                     })
    #         mls = self.move_line_ids
    #
    #     # qty_done را پر کن و مقصد را روی سبد بگذار
    #     for ml in mls:
    #         if not ml.qty_done or ml.qty_done <= 0.0:
    #             qty_needed = getattr(ml, 'reserved_uom_qty',
    #                                  0.0) or ml.product_uom_qty or ml.move_id.product_uom_qty or 0.0
    #             if qty_needed > 0:
    #                 ml.qty_done = qty_needed
    #         ml.result_package_id = package.id
    #     return True

    def action_print_receipt_lot_labels(self):
        self.ensure_one()

        # فقط سریال/لات‌هایی که در همین رسید ثبت شده‌اند
        # (stock.move.line روی همین picking)
        move_lines = self.move_line_ids
        lots = move_lines.mapped('lot_id')
        lots = lots.filtered(lambda l: l)  # حذف False

        # اگر هنوز validate نشده و lot_id ساخته/ست نشده باشد پیغام بده
        if not lots:
            raise UserError(_("هیچ شماره سریالی برای این رسید پیدا نشد. "
                              "اگر رسید را هنوز تایید نکرده‌اید، ابتدا تایید کنید تا سریال‌ها ساخته و روی خطوط ست شوند."))

        # مرتب‌سازی اختیاری: اول کالا، بعد نام سریال
        lots = lots.sorted(key=lambda l: (l.product_id.display_name or '', l.name or ''))

        # استفاده از همان گزارش موجود شما
        action = self.env.ref('artarad_kadolin_custom.action_report_lot_label')
        # report_action خودش model = stock.lot را رعایت می‌کند
        return action.report_action(lots)

    def action_create_serial_numbers(self):
        for picking in self:
            if picking.picking_type_code != 'incoming':
                raise UserError(_("This shortcut is intended for incoming pickings."))

            for move in picking.move_ids.filtered(
                    lambda m: m.product_id.tracking == 'serial' and m.product_uom_qty > 0):
                # تعداد سریال = تعداد سفارش برای این موو
                qty = int(move.product_uom_qty)

                # اگر قبلاً move line ساخته شده و lot دارد، می‌توانی پاک کنی یا رد شوی (به انتخاب)
                if move.move_line_ids:
                    move.move_line_ids.unlink()

                # کانتکست لازم برای جنریت
                ctx = {
                    'default_product_id': move.product_id.id,
                    'default_company_id': move.company_id.id,
                    'default_picking_id': picking.id,
                    'default_picking_type_id': picking.picking_type_id.id,
                    'default_location_id': move.location_id.id,
                    'default_location_dest_id': move.location_dest_id.id,
                    'default_quantity': qty,  # مقدار کل برای محاسبهٔ تقسیم
                    'default_tracking': 'serial',  # حتماً سریالی
                }

                # صدا زدن متد شما که لیست vals می‌دهد (به امضای خودتان توجه کنید)
                # اگر متد شما روی stock.move.line تعریف شده، از env آن را بخوانید.
                vals_list = self.env['stock.move'].action_generate_lot_line_vals(
                    ctx, 'generate', False, qty, ''
                )

                # تبدیل خروجی به vals مناسب create() روی move line
                cleaned_vals = []
                for vals in vals_list:
                    v = dict(vals)

                    # اگر خروجی شما بعضی فیلدها را به‌صورت دیکشنری {'id':..,'display_name':..} برگرداند، به id کاهش بده:
                    for f in ('product_id', 'location_id', 'location_dest_id', 'picking_id', 'company_id',
                              'product_uom_id'):
                        if isinstance(v.get(f), dict):
                            v[f] = v[f]['id']

                    # اتصال به این move و picking
                    v['move_id'] = move.id
                    v['picking_id'] = picking.id

                    # برای حوالهٔ ورودی: اگر v شامل lot_name است، خود Odoo موقع validate، Lot را می‌سازد
                    # پس کافیست qty_done = 1 (یا quantity برگردانده‌شده) ست شود
                    v['qty_done'] = v.get('quantity', 1) or 1

                    cleaned_vals.append(v)

                if cleaned_vals:
                    self.env['stock.move.line'].create(cleaned_vals)

        return True

    def _assign_pack_carrier(self):
        for rec in self.filtered(lambda l: l._is_pack() ):
            order = self.env['sale.order'].sudo().search([('name','=',rec.origin)],limit=1)
            if not order or  order.user_id:
                continue
            city = rec.partner_id.city_id
            domain = [('use_for_pack', '=', True)]
            carriers = self.env['delivery.carrier'].search(domain)
            if not carriers:
                continue
            eligible = []
            for c in carriers:
                if not c.supported_city_ids or city in c.supported_city_ids:
                    eligible.append(c)
            if not eligible:
                continue

            today_packs = self.env['stock.picking'].search([
                ('create_date', '>=', fields.Date.today()),
            ]).filtered(lambda l:l._is_pack())
            count_by_carrier = {c.id: len(today_packs.filtered(lambda o: o.carrier_id == c)) for c in eligible}
            min_carrier = min(count_by_carrier, key=count_by_carrier.get)
            selected = self.env['delivery.carrier'].browse(min_carrier)
            rec.carrier_id = selected.id


class StockLot(models.Model):
    _inherit = "stock.lot"

    name = fields.Char(
        'Lot/Serial Number', default=lambda self: self.env['ir.sequence'].next_by_code('stock.lot.serial'),
        required=True,readonly=1, help="Unique Lot/Serial Number", index='trigram')
    # @api.model
    # def create(self, vals):
    #     if 'name' in vals:
    #        vals['ref'] = vals['name']
    #        vals['name'] = self.env['ir.sequence'].next_by_code('stock.lot.serial')
    #     return super(StockLot, self).create(vals)


    @api.constrains('name', 'company_id')
    def _check_unique_name_company(self):
        for rec in self:
            if not rec.name :
                continue
            dup = self.search([
                ('id', '!=', rec.id),
                ('name', '=', rec.name),

            ], limit=1)
            if dup:
               raise UserError(_("Serial/Lot '%s' already exists '. It must be unique.")
                                      % (rec.name))

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    use_for_pack = fields.Boolean(string="استفاده برای پَک‌ها", default=False)
    pack_distribution_percent = fields.Float(string="درصد تخصیص برای پَک‌ها",
                                             help="درصد سهم این روش حمل در توزیع سفارشات پکی")
    supported_city_ids = fields.Many2many(
        'res.city', 'carrier_supported_city_rel', 'carrier_id', 'city_id',
        string="شهرهای پشتیبانی‌شده",
        help="اگر خالی باشد یعنی تمام شهرها مجازند."
    )

    def _slot_availability(self, order, start_date=None, horizon_days=30, needed_free_days=5):
        """برمی‌گرداند آرایه‌ای از دیکشنری‌ها برای هر روز:
           [{'date': '2025-10-30', 'used': 7, 'capacity': 20, 'status': 'free'|'full'}, ...]
           - شمارش بر اساس تعداد سفارش‌هایی که حداقل یک سطر با محصول روش حمل دارند.
           - groupby روی sale.order.select_deliver_date
        """
        self.ensure_one()
        if not start_date:
            start_date = (order.expected_date or fields.Date.today())
            if isinstance(start_date, str):
                start_date = fields.Date.from_string(start_date)

        # محصول/محصولاتِ روش حمل (بسته به پیاده‌سازی خودت)
        carrier_products = self.product_id
        if not carrier_products:
            return []

        cap = max(getattr(self, 'daily_capacity', 0) or getattr(self, 'delivery_daily_capacity', 0) or 0, 0)

        # بازهٔ زمانی برای جست‌وجو (برای پیدا کردن «۵ روزِ خالی بعدی» تا مثلاً 30 روز آینده می‌گردیم)
        date_from = start_date
        date_to = start_date + timedelta(days=horizon_days)

        # فقط سفارش‌های «قطعی/انجام‌شده» را حساب کنیم (اگر لازم است draft/quotation را هم لحاظ کنی، این را تغییر بده)
        domain = [
            ('company_id', '=', order.company_id.id),
            ('state', 'in', ['sale', 'done']),
            ('select_deliver_date', '>=', date_from),
            ('select_deliver_date', '<=', date_to),
            ('order_line.product_id', 'in', carrier_products.ids),
        ]

        # groupby روی خود فیلد تاریخِ سفارش (روی sale.order هست)
        rows = self.env['sale.order'].read_group(
            domain=domain,
            fields=['id:count'],
            groupby=['select_deliver_date'],
            lazy=False,
        )
        # خروجی read_group: هر ردیف کلید 'select_deliver_date' و 'id_count' دارد
        counted = {r['select_deliver_date']: r['id_count'] for r in rows}

        # حالا از date_from به بعد را قدم‌به‌قدم می‌سازیم تا وقتی 5 روز «free» جمع کنیم
        out = []
        free_collected = 0
        cur = date_from
        days_seen = 0
        while days_seen < horizon_days and free_collected < needed_free_days:
            used = int(counted.get(cur, 0))
            status = 'free' if (cap == 0 or used < cap) else 'full'
            out.append({
                'date': cur.isoformat(),
                'used': used,
                'capacity': cap,
                'status': status,
            })
            if status == 'free':
                free_collected += 1
            cur += timedelta(days=1)
            days_seen += 1



        return out