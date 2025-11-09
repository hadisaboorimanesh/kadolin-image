# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
import logging
from odoo import SUPERUSER_ID
import secrets
import string
_logger = logging.getLogger(__name__)
import time
from odoo import Command, modules
from odoo import fields
from odoo.exceptions import UserError
from werkzeug.urls import url_encode
from odoo.addons.payment.controllers import portal as payment_portal

_otp_throttle_map = {}

def _touch_throttle(mobile, cooldown_sec=120):
    """Check & update throttle in a single transaction, safe for multi-worker."""
    env = request.env
    cr = env.cr
    now = fields.Datetime.now()

    # قفل خوش‌رفتار روی ردیف (اگر وجود دارد)
    cr.execute("""
        SELECT id, last_sent
          FROM ak_otp_throttle
         WHERE mobile = %s
         FOR UPDATE
    """, [mobile])
    row = cr.fetchone()

    if row:
        rec_id, last_sent = row
        # اختلاف زمانی (ثانیه)
        delta = (now - last_sent).total_seconds()
        if delta < cooldown_sec:
            wait = int(cooldown_sec - delta)
            raise UserError(_("کد قبلاً ارسال شده است، لطفاً %(s)s ثانیه دیگر تلاش کنید.", s=wait))
        cr.execute("UPDATE ak_otp_throttle SET last_sent=%s WHERE id=%s", [now, rec_id])
    else:
        cr.execute("INSERT INTO ak_otp_throttle (mobile, last_sent) VALUES (%s, %s)", [mobile, now])


def _send_sms_otp(mobile, message=None, cooldown=120, timeout=None):
    """Send OTP SMS with throttle and failover; raises UserError on problems.
    `timeout` is accepted for future use but ignored to avoid provider signature mismatch.
    """
    # throttle (may raise UserError with remaining seconds)
    _touch_throttle(mobile, cooldown)
    _logger.info("Code : %s", message)

    Provider = request.env["artarad.sms.provider.setting"].sudo()
    providers = Provider.search([], order="sequence asc")
    if not providers:
        _logger.warning("هیچ پروایدری برای ارسال پیامک تعریف نشده است.")
        raise UserError(_("هیچ سرویس پیامکی پیکربندی نشده است."))

    provider = providers[0] if len(providers) == 1 else providers[1]

    # Provider = request.env["artarad.sms.provider.setting"].sudo()
    # providers = Provider.search([], order="sequence asc")

    _logger.info("Sending OTP to %s; providers count=%s", mobile, len(providers))

    last_exc = None
    # for provider in providers:
    try:
        send_method_name = f"send_sms_by_{provider.provider}"
        if hasattr(provider, send_method_name):
            send_method = getattr(provider, send_method_name)
            # عمداً پارامتر timeout پاس نمی‌دهیم تا با امضاهای مختلف تداخل نکند
            send_method(mobile, message)
        else:
            provider.send_sms(mobile, message)
        _logger.info("OTP sent to %s via provider [%s]", mobile, provider.provider)
        return True
    except Exception as e:
        last_exc = e
        _logger.exception("Provider %s failed to send OTP to %s", provider.provider, mobile)
        # try next provider

    # اگر همهٔ پروایدرها خطا دادند
    raise UserError(_("ارسال پیامک با خطا مواجه شد. لطفاً کمی بعد دوباره تلاش کنید."))


def _norm(m):
    from ..models.res_users import _normalize_mobile
    return _normalize_mobile(m)

def _set_user_password_strong(user, raw_password):
    """Odoo 18 — فقط از متد رسمی خود Odoo برای ست‌کردن پسورد استفاده کن."""
    user = user.sudo()
    user.password = raw_password
    # user.write({'password': raw_password})
    # user._set_password()

def _set_user_password(user, raw_password):
    """Odoo 18: ست‌کردن پسورد با ادمین و نهایی‌سازی هش."""
    UsersSU = request.env['res.users'].with_user(SUPERUSER_ID)
    u = UsersSU.browse(user.id)
    u.password = raw_password        # مقدار کلیر روی فیلد transient
    u._set_password()                # تولید و ذخیره password_crypt
    request.env.cr.commit()          # مهم: تا در Registry جدید authenticate دیده شود

def _rand_password(length=8):
    # پسورد ساده شامل حروف و عدد (می‌تونی پیچیده‌ترش کنی)
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

class AKMobileLogin(http.Controller):

    @http.route(['/ak/login'], type='http', auth='public', website=True, csrf=True)
    def ak_login(self, **kw):
        # اگر کاربر لاگین است (عمومی/public نیست) => برگردان به صفحه اول
        if not request.website.is_public_user():
            return request.redirect('/')

        # در غیر این صورت فرم لاگین را نشان بده
        resp = request.render('ak_mobile_login.ak_login_mobile', {})
        # جلوگیری از کش شدن فرم (توکن CSRF تازه بماند)
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
        return resp

    # هندل GET برای جلوگیری از خطای ناخواسته
    @http.route(['/ak/login/check'], type='http', auth='public', methods=['GET'], website=True, csrf=False)
    def ak_login_check_get(self, **kw):
        return request.redirect('/ak/login')

    @http.route(['/ak/login/check'], type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def ak_login_check(self, **post):
        try:
            mobile = _norm(post.get('mobile'))
            if not mobile:
                return request.redirect('/ak/login')

            Users = request.env['res.users'].sudo()
            user = Users.find_by_mobile(mobile)

            def _is_temp(u):
                try:
                    return (
                            not u.active
                            or (u.login or "").startswith("temp_")
                            or (u.name or "").strip() in (f"Temp {mobile}", f"temp {mobile}")
                    )
                except Exception:
                    return False

            if user:
                if _is_temp(user):
                    return request.render('ak_mobile_login.ak_signup_form', {'mobile': mobile})
                return request.redirect('/ak/login/password?' + url_encode({'mobile': mobile}))
            try:
                portal = request.env.ref('base.group_portal')
                user = Users.create({
                    'name': f'Temp {mobile}',
                    'login': mobile,
                    'login_mobile': mobile,
                    'lang': 'fa_IR',
                    'phone': mobile,
                    'mobile': mobile,
                    'active': False,
                    'share': True,
                    'groups_id': [(6, 0, [portal.id])],
                })
            except Exception:
                request.env.cr.rollback()
                user = Users.find_by_mobile(mobile)
                if not user:
                    _logger.exception("Create user failed and refind returned nothing")
                    return request.redirect('/ak/login')  # پیام کاربرپسند در صفحه‌ی فرم

            # کد OTP
            try:
                code = user.sudo().action_generate_otp()
            except Exception:
                request.env.cr.rollback()
                _logger.exception("action_generate_otp failed")
                return request.render('ak_mobile_login.ak_login_mobile', {
                    'mobile': mobile,
                    'error': _("مشکلی در تولید کد رخ داد. کمی بعد دوباره تلاش کنید."),
                })

            # ارسال SMS و نمایش خطاهای مرتبط (مثل محدودیت ۲ دقیقه)
            try:
                _send_sms_otp(mobile, f"کادولین - کد ورود شما: {code}")
            except UserError as e:
                return request.render('ak_mobile_login.ak_login_mobile', {
                    'mobile': mobile,
                    'error': str(e),
                })
            except Exception:
                _logger.exception("OTP SMS send failed for %s", mobile)
                return request.render('ak_mobile_login.ak_login_mobile', {
                    'mobile': mobile,
                    'error': _("ارسال پیامک با خطا مواجه شد. لطفاً کمی بعد دوباره تلاش کنید."),
                })

            return request.redirect('/ak/login/otp?' + url_encode({'mobile': mobile, 'flow': 'signup'}))

        except Exception:
            _logger.exception("ak_login_check unexpected error; post")
            # پیام عمومی ولی بی‌خطا برای کاربر
            return request.redirect('/ak/login')

    # @http.route(['/ak/login/check'], type='http', auth='public', methods=['POST'], website=True, csrf=True)
    # def ak_login_check(self, **post):
    #     mobile = (post.get('mobile') or '').strip()
    #     if not mobile:
    #         return request.redirect('/ak/login')
    #
    #     mobile = _norm(mobile)
    #     if not mobile:
    #         return request.redirect('/ak/login')
    #
    #     Users = request.env['res.users'].sudo()
    #     user = Users.find_by_mobile(mobile)
    #
    #     if user:
    #         return request.redirect('/ak/login/password?mobile=%s' % mobile)
    #     else:
    #
    #         user = Users.sudo().create({
    #             'name': 'Temp %s' % mobile,
    #             'login': mobile,
    #             'login_mobile': mobile,
    #             'active': False,
    #         })
    #         code = user.sudo().action_generate_otp()
    #         _send_sms_otp(mobile,f"کادولین - کد ورود شما: {code}")
    #         return request.redirect('/ak/login/otp?mobile=%s&flow=signup' % mobile)

    # مرحله ۲: فرم رمز عبور
    @http.route(['/ak/login/password'], type='http', auth='public', website=True, csrf=True)
    def ak_password_form(self, **kw):
        mobile = _norm(kw.get('mobile') or '')
        if not mobile:
            return request.redirect('/ak/login')
        return request.render('ak_mobile_login.ak_login_password', {'mobile': mobile})

    @http.route(['/ak/login/password/do'], type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def ak_do_password(self, **post):
        mobile = _norm(post.get('mobile') or '')
        password = post.get('password')
        if not mobile or not password:
            return request.redirect('/ak/login')

        Users = request.env['res.users'].sudo()
        user = Users.find_by_mobile(mobile)
        if not user:
            return request.redirect('/ak/login')

        try:
            # uid = request.session.authenticate(request.session.db, user.login, password)
            credentials = {'login': user.login, 'password': password, 'type': 'password'}
            uid = request.session.authenticate(request.db, credentials)
        except Exception:
            uid = False


        if uid:
            return request.redirect('/shop/cart')
        return request.render('ak_mobile_login.ak_login_password', {
            'mobile': mobile,
            'error': _('رمز عبور نادرست است.'),
        })

    # مرحله ۳: OTP
    @http.route(['/ak/login/otp'], type='http', auth='public', website=True, csrf=True)
    def ak_otp_form(self, **kw):
        mobile = _norm(kw.get('mobile') or request.session.get('ak_mobile') or '')
        flow = kw.get('flow') or 'login'
        if not mobile:
            return request.redirect('/ak/login')

        # اگر کاربر صراحتاً resend بخواهد حتی اگر sent=1 باشد، یک بار دیگر ارسال کن
        if flow == 'login' and kw.get('resend') == '1':
            try:
                user = request.env['res.users'].sudo().with_context(active_test=False).find_by_mobile(mobile)
                if user and user.active:
                    code = user.sudo().action_generate_otp()
                    _send_sms_otp(mobile, f"کد ورود شما در کادولین: {code}")  # Throttle رعایت می‌شود
            except UserError as e:
                return request.render('ak_mobile_login.ak_login_otp', {'mobile': mobile, 'flow': flow, 'error': str(e)})
            except Exception:
                _logger.exception("Resend OTP failed for %s", mobile)
                return request.render('ak_mobile_login.ak_login_otp', {'mobile': mobile, 'flow': flow, 'error': _(
                    "ارسال پیامک با خطا مواجه شد. لطفاً کمی بعد تلاش کنید.")})
            # بعد از ارسال مجدد هم بهتره sent=1 بمونه
            return request.redirect(f"/ak/login/otp?mobile={mobile}&flow=login&sent=1")

        # ارسال خودکار فقط بارِ اول (وقتی sent != 1)
        if flow == 'login' and kw.get('sent') != '1':
            try:
                user = request.env['res.users'].sudo().with_context(active_test=False).find_by_mobile(mobile)
                if user and user.active:
                    code = user.sudo().action_generate_otp()
                    _send_sms_otp(mobile, f"کد ورود شما در کادولین: {code}")
            except UserError as e:
                return request.render('ak_mobile_login.ak_login_otp', {'mobile': mobile, 'flow': flow, 'error': str(e)})
            except Exception:
                _logger.exception("Auto-send OTP failed for %s", mobile)
                return request.render('ak_mobile_login.ak_login_otp', {'mobile': mobile, 'flow': flow, 'error': _(
                    "ارسال پیامک با خطا مواجه شد. لطفاً کمی بعد دوباره تلاش کنید.")})
            return request.redirect(f"/ak/login/otp?mobile={mobile}&flow=login&sent=1")

        return request.render('ak_mobile_login.ak_login_otp', {'mobile': mobile, 'flow': flow})

    @http.route(['/ak/login/otp/verify'], type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def ak_verify_otp(self, **post):
        mobile = _norm(post.get('mobile') or '')
        code = (post.get('otp') or '').strip()
        flow = post.get('flow') or 'login'

        if not mobile or not code:
            return request.redirect('/ak/login')

        Users = request.env['res.users'].sudo()
        user = Users.find_by_mobile(mobile)
        if not user:
            return request.redirect('/ak/login')

        if not user.action_check_otp(code):
            return request.render('ak_mobile_login.ak_login_otp', {
                'mobile': mobile,
                'flow': flow,
                'error': _('کد تایید نامعتبر یا منقضی است.'),
            })

        # ✅ در این مرحله OTP معتبر است
        # اگر کاربر تازه است (signup)
        if flow == 'signup' or not user.active:
            user.sudo().write({'active': True})
            return request.redirect('/ak/signup?mobile=%s' % mobile)

        # ✅ لاگین رسمی مثل هستهٔ Odoo: finalize با env کاربر
        env_user = request.env(user=user.id)
        # پیش‌نیاز finalize: این دو مقدار باید روی سشن ست شوند
        request.session['pre_login'] = user.login
        request.session['pre_uid'] = user.id
        request.session.finalize(env_user)
        request.env = env_user
        request.env.cr.commit()
        _logger.info("User %s logged in via OTP successfully (finalize)", user.login)
        return request.redirect('/shop/cart')

    # مرحله ۴: ثبت‌نام
    @http.route(['/ak/signup'], type='http', auth='public', website=True, csrf=True)
    def ak_signup_form(self, **kw):
        mobile = _norm(kw.get('mobile') or '')
        if not mobile:
            return request.redirect('/ak/login')
        return request.render('ak_mobile_login.ak_signup_form', {'mobile': mobile})

    @http.route(['/ak/signup/do'], type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def ak_signup_do(self, **post):
        mobile = _norm(post.get('mobile') or '')
        name = (post.get('name') or mobile)
        password = post.get('password')

        if not mobile or not password:
            return request.redirect('/ak/login')

        Users = request.env['res.users'].sudo()
        user = Users.find_by_mobile(mobile)
        portal = request.env.ref('base.group_portal')

        if user:

            user.sudo().write({'name': name, 'login': mobile,
                               'phone': mobile,
                'mobile': mobile,'lang': 'fa_IR','active': True,'share': True,
                'groups_id': [(6, 0, [portal.id])]})
        else:
            user = Users.sudo().create({
                'name': name,
                'lang': 'fa_IR',
                'login': mobile,
                'phone': mobile,
                'mobile': mobile,
                'login_mobile': mobile,
                'active': True,
                'share': True,
                'groups_id': [(6, 0, [portal.id])],
            })

        _set_user_password_strong(user, password)
        request.env.cr.commit()
        credentials = {'login': user.login, 'password': password, 'type': 'password'}
        uid = request.session.authenticate(request.db, credentials)
        if uid:
            redirect = request.params.get('redirect') or request.httprequest.args.get('redirect')

            if not redirect:
                redirect =  '/shop/cart'

            return request.redirect(redirect)

        return request.redirect('/ak/login')

    @http.route(['/ak/login/reset'], type='http', auth='public', website=True, csrf=True)
    def ak_reset_form(self, **kw):
        mobile = _norm(kw.get('mobile') or request.session.get('ak_mobile') or '')
        return request.render('ak_mobile_login.ak_reset_mobile', {'mobile': mobile})

    @http.route(['/ak/login/reset/otp'], type='http', auth='public', website=True, csrf=True)
    def ak_reset_otp_form(self, **kw):
        mobile = _norm(kw.get('mobile') or '')
        if not mobile:
            return request.redirect('/ak/login/reset')

        # موبایل را در سشن نگه داریم تا در مراحل بعدی دستکاری نشود
        request.session['ak_reset_mobile'] = mobile

        Users = request.env['res.users'].sudo()
        user = Users.find_by_mobile(mobile)
        if not user or not user.active:
            # کاربر پیدا نشد یا فعال نیست
            return request.render('ak_mobile_login.ak_reset_mobile', {
                'error': _('کاربری با این شماره یافت نشد.'),
                'mobile': mobile,
            })

        # ارسال کد
        code = user.sudo().action_generate_otp()
        _send_sms_otp(mobile, f"کادولین- کد تایید تغییر رمز شما: : {code}")
        return request.render('ak_mobile_login.ak_reset_otp', {
            'mobile': mobile,
        })

    @http.route(['/ak/login/reset/verify'], type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def ak_reset_verify(self, **post):
        mobile = _norm(post.get('mobile') or request.session.get('ak_reset_mobile') or '')
        code = (post.get('otp') or '').strip()
        if not mobile or not code:
            return request.redirect('/ak/login/reset')

        Users = request.env['res.users'].sudo()
        user = Users.find_by_mobile(mobile)
        if not user or not user.active:
            return request.redirect('/ak/login/reset')

        if not user.action_check_otp(code):
            return request.render('ak_mobile_login.ak_reset_otp', {
                'mobile': mobile,
                'error': _('کد تایید نامعتبر یا منقضی است.'),
            })

        # OTP درست → نمایش فرم رمز جدید
        return request.render('ak_mobile_login.ak_reset_new_password', {
            'mobile': mobile,
        })

    @http.route(['/ak/login/reset/do'], type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def ak_reset_do(self, **post):
        mobile = _norm(post.get('mobile') or request.session.get('ak_reset_mobile') or '')
        new_pass = (post.get('password') or '').strip()
        confirm = (post.get('confirm_password') or '').strip()

        if not mobile or not new_pass:
            return request.redirect('/ak/login/reset')

        if new_pass != confirm:
            return request.render('ak_mobile_login.ak_reset_new_password', {
                'mobile': mobile,
                'error': _('رمز عبور و تکرار آن یکسان نیستند.'),
            })

        Users = request.env['res.users'].sudo()
        user = Users.find_by_mobile(mobile)
        if not user or not user.active:
            return request.redirect('/ak/login/reset')

        # ست‌کردن رمز با متد رسمی‌ای که قبلاً در ماژولت داری
        _set_user_password_strong(user, new_pass)
        request.env.cr.commit()

        # هدایت به فرم ورود با موبایل (می‌تونی پیام هم نشان بدهی)
        return request.redirect('/ak/login/password?mobile=%s' % mobile)

    @http.route(['/ak/login/reset/instant'], type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def ak_reset_instant(self, **post):
        mobile = _norm(post.get('mobile') or '')
        if not mobile:
            return request.redirect('/ak/login/reset')

        Users = request.env['res.users'].sudo()
        user = Users.find_by_mobile(mobile)
        if not user or not user.active:
            return request.render('ak_mobile_login.ak_reset_mobile', {
                'error': _('کاربری با این شماره یافت نشد.'),
                'mobile': mobile,
            })

        # ساخت رمز جدید و ارسال
        new_pass = _rand_password(8)
        _set_user_password_strong(user, new_pass)
        request.env.cr.commit()

        # ارسال رمز با SMS
        try:
            _send_sms_otp(mobile, f"New Password: {new_pass}")
        except Exception:
            _logger.exception("Sending new password SMS failed for %s", mobile)

        # هدایت به فرم ورود با موبایل
        return request.redirect('/ak/login/password?mobile=%s' % mobile)

    @http.route(['/ak/login/otp/send'], type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def ak_send_otp(self, **post):
        """
        ارسال کد تأیید (OTP) برای ورود یا ثبت‌نام.
        شامل کنترل ضد اسپم (۲ دقیقه محدودیت بین ارسال‌ها).
        """
        mobile = _norm(post.get('mobile') or request.session.get('ak_mobile') or '')
        flow = post.get('flow') or 'login'

        if not mobile:
            return request.redirect('/ak/login')

        Users = request.env['res.users'].sudo()
        user = Users.with_context(active_test=False).find_by_mobile(mobile)

        # اگر کاربر وجود ندارد، یکی موقت می‌سازیم
        if not user:
            user = Users.sudo().create({
                'name': f'Temp {mobile}',
                'login': mobile,
                'login_mobile': mobile,
                'active': False,
            })

        try:
            code = user.sudo().action_generate_otp()
            _send_sms_otp(mobile, f"کادولین- کد تایید شما: {code}")
        except Exception as e:
            return request.render('ak_mobile_login.ak_login_otp', {
                'mobile': mobile,
                'flow': flow,
                'error': str(e),  # پیام خطا (مثلاً: «کد قبلاً ارسال شده است، لطفاً کمی صبر کنید»)
            })

        # ذخیره در سشن برای مرحله بعدی
        request.session['ak_mobile'] = mobile

        _logger.info("OTP sent to %s for flow=%s", mobile, flow)

        return request.redirect(f'/ak/login/otp?mobile={mobile}&flow={flow}&sent=1')

class WebsiteSale(payment_portal.PaymentPortal):

    def _check_cart(self, order_sudo):
        """ Check whether the cart is a valid, and redirect to the appropriate page if not.

        The cart is only valid if:

        - it exists and is in the draft state;
        - it contains products (i.e., order lines);
        - either the user is logged in, or public orders are allowed.

        :param sale.order order_sudo: The cart to check.
        :return: None if the cart is valid; otherwise, a redirection to the appropriate page.
        """
        # Check that the cart exists and is in the draft state.
        if not order_sudo or order_sudo.state != 'draft':
            request.session['sale_order_id'] = None
            request.session['sale_transaction_id'] = None
            return request.redirect('/shop/cart')

        # Check that the cart is not empty.
        if not order_sudo.order_line:
            return request.redirect('/shop/cart')

        # Check that public orders are allowed.
        if request.env.user._is_public() and request.website.account_on_checkout == 'mandatory':
            return request.redirect('/ak/login?redirect=/shop/checkout')

