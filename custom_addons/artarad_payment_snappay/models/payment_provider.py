# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import time

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

VERIFY_OK_STATES   = {'VERIFY', 'VERIFIED', 'VERIFY_SUCCESS'}
SETTLED_STATES     = {'SETTLE', 'SETTLED', 'SETTLED_SUCCESS'}
PENDING_STATES     = {'PENDING', 'VERIFY_PENDING'}

def _is_success_flag(payload: dict, default=False):
    # بعضی اندپوینت‌ها successful ندارند؛ در پرداخت بهتره default=False باشه
    try:
        return bool(payload.get('successful', default))
    except Exception:
        return False

def _normalize_status(payload: dict):
    st = payload.get('status') or payload.get('transactionStatus') or payload.get('state')
    if isinstance(st, str):
        return st.strip().upper()
    return None

def _must_retry(status):
    return (status in PENDING_STATES)

def _jsonify_response(resp):
    if isinstance(resp, dict):
        return resp
    try:
        return resp.json()
    except Exception:
        return {'raw': str(resp)}

def _safe_store_settle_status(orders, payload):
    try:
        txt = json.dumps(payload, ensure_ascii=False)
        orders.write({'settle_status': txt})
    except Exception:
        _logger.exception("Failed to write settle_status")

def _poll_once_then_backoff(fetch_fn, max_attempts=2, wait_seconds=3):
    # fetch_fn باید callable باشه که dict برگردونه
    payload = fetch_fn()
    if payload is None:
        payload = {}
    if max_attempts <= 1:
        return payload

    status = _normalize_status(payload)
    attempts = 1
    while attempts < max_attempts and _must_retry(status):
        time.sleep(wait_seconds)
        payload = fetch_fn() or {}
        status = _normalize_status(payload)
        attempts += 1
    return payload



class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    snappay_title_message = fields.Char(string="SnappPay Title (dynamic)", compute="_compute_snappay_dynamic_texts",
                                        store=False)
    snappay_description_message = fields.Char(string="SnappPay Description (dynamic)",
                                              compute="_compute_snappay_dynamic_texts", store=False)

    # ثبت کُد پروایدر
    code = fields.Selection(
        selection_add=[('snappay', "SnappPay")],
        ondelete={'snappay': 'set default'},
    )

    # ====== تنظیمات SnappPay ======
    # در SnappPay عملاً دو محیط داریم: تست و تولید. برای سادگی یک base_url می‌گیریم.
    snappay_base_url = fields.Char(
        string="SnappPay Base URL",
        help="Base URL like: https://<host> (without trailing slash)",
        required_if_provider='snappay',
    )
    snappay_client_id = fields.Char(
        string="SnappPay Client ID",
        required_if_provider='snappay',
    )
    snappay_client_secret = fields.Char(
        string="SnappPay Client Secret",
        groups='base.group_system',
        required_if_provider='snappay',
    )
    snappay_username = fields.Char(
        string="SnappPay Username",
        required_if_provider='snappay',
    )
    snappay_password = fields.Char(
        string="SnappPay Password",
        groups='base.group_system',
        required_if_provider='snappay',
    )
    snappay_return_url = fields.Char(
        string="SnappPay Return URL",
        help="Relative path handled by your controller (e.g. /payment/snappay/return)",
        default='/payment/snappay/return',
        required_if_provider='snappay',
    )

    # ====== قیدها / اعتبارسنجی‌ها ======

    @api.constrains('snappay_base_url', 'snappay_client_id', 'snappay_client_secret',
                    'snappay_username', 'snappay_password', 'state')
    def _check_snappay_required_when_active(self):
        """وقتی پروایدر SnappPay فعال است، همه‌ی فیلدهای لازم باید پر باشند."""
        for provider in self.filtered(lambda p: p.code == 'snappay' and p.state != 'disabled'):
            missing = []
            if not provider.snappay_base_url:
                missing.append("Base URL")
            if not provider.snappay_client_id:
                missing.append("Client ID")
            if not provider.snappay_client_secret:
                missing.append("Client Secret")
            if not provider.snappay_username:
                missing.append("Username")
            if not provider.snappay_password:
                missing.append("Password")
            if missing:
                raise ValidationError(_("SnappPay: Missing required fields: %s") % ", ".join(missing))

    # AsiaPay یک محدودیت ارز داشت؛ SnappPay چنین محدودیتی ندارد. قیدی اضافه نمی‌کنیم.

    # ====== توابع کمکی SnappPay برای کال‌های API ======

    def _snappay_api_url(self, path):
        """ساخت URL کامل برای endpointهای SnappPay."""
        self.ensure_one()
        base = (self.snappay_base_url or '').rstrip('/')
        if not base:
            raise UserError(_("SnappPay base URL is not configured."))
        if not path.startswith('/'):
            path = '/' + path
        return f"{base}{path}"

    def _snappay__jwt_cache_key(self):
        self.ensure_one()
        env_key = 'prod' if self.state == 'enabled' else 'test'
        return f"payment.snappay.jwt.{env_key}.provider_{self.id}"

    def _snappay_get_jwt(self, force_refresh=False):
        """
        JWT را می‌گیرد/نوسازی می‌کند:
          POST /api/online/v1/oauth/token
          Headers:
            Authorization: Basic base64({client_id}:{client_secret})
            Content-Type: application/x-www-form-urlencoded
          Body:
            grant_type=password&scope=online-merchant&username=...&password=...
        """
        self.ensure_one()
        icp = self.env['ir.config_parameter'].sudo()
        cache_key = self._snappay__jwt_cache_key()
        if not force_refresh:
            cached = icp.get_param(cache_key)
            if cached:
                try:
                    token_data = json.loads(cached)
                    # expires_in ~3600; اگر هنوز معتبر است از همان استفاده کن
                    if token_data.get('access_token') and token_data.get('exp_ts', 0) > time.time() + 30:
                        return token_data['access_token']
                except Exception:
                    pass

        # درخواست توکن
        url = self._snappay_api_url('/api/online/v1/oauth/token')
        auth_basic = requests.auth.HTTPBasicAuth(self.snappay_client_id, self.snappay_client_secret)
        data = {
            'grant_type': 'password',
            'scope': 'online-merchant',
            'username': self.snappay_username,
            'password': self.snappay_password,
        }
        try:
            resp = requests.post(url, auth=auth_basic, data=data, timeout=30)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as e:
            _logger.exception("SnappPay: JWT request failed")
            raise UserError(_("Failed to obtain SnappPay token: %s") % e)

        access_token = payload.get('access_token')
        expires_in = int(payload.get('expires_in') or 3600)
        if not access_token:
            raise UserError(_("SnappPay: No access_token in response."))

        icp.set_param(cache_key, json.dumps({
            'access_token': access_token,
            'exp_ts': time.time() + expires_in,  # زمان انقضای تقریبی
        }))
        return access_token

    def _snappay_request(self, path, json_body=None, method='POST', retry_on_401=True, timeout=60):
        """کال عمومی SnappPay با JWT در هدر."""
        self.ensure_one()
        token = self._snappay_get_jwt(force_refresh=True)
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        url = self._snappay_api_url(path)
        try:
            if method == 'POST':
                resp = requests.post(url, headers=headers, json=json_body or {}, timeout=timeout)
            else:
                resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 401 and retry_on_401:
                token = self._snappay_get_jwt(force_refresh=True)
                headers['Authorization'] = f'Bearer {token}'
                if method == 'POST':
                    resp = requests.post(url, headers=headers, json=json_body or {}, timeout=timeout)
                else:
                    resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout as e:
            _logger.exception("SnappPay API call failed [%s]: %s", path, e)
        except Exception as e:
            _logger.exception("SnappPay API call failed [%s]: %s", path, e)
            # raise UserError(_("SnappPay API call failed for %s: %s") % (path, e))

    # ====== سرویس‌های متداول SnappPay (برای استفاده از تراکنش) ======

    def snappay_get_payment_token(self, *, amount, cart_list, return_url, transaction_id,
                                  discount_amount=0, external_source_amount=0,
                                  payment_method_type="INSTALLMENT", mobile=None):

        self.ensure_one()

        body = {
            "amount": int(amount or 0),
            "discountAmount": int(discount_amount or 0),
            "externalSourceAmount": int(external_source_amount or 0),
             "mobile": mobile or "",
            "paymentMethodTypeDto": payment_method_type or "INSTALLMENT",
            "returnURL": return_url or self.snappay_return_url,
            "transactionId": transaction_id,  # یونیک سمت مرچنت
            "cartList": cart_list or [],
        }
        res = self._snappay_request('/api/online/payment/v1/token', json_body=body, method='POST')
        if not (res or {}).get('successful'):
            raise UserError(_("SnappPay token request failed: %s") % (res,))
        return (res['response'] or {}).get('paymentToken'), (res['response'] or {}).get('paymentPageUrl')


    def _snappay_extract_status(self, res):
        """Return upper-cased status code from any SnappPay JSON response shape.
        Looks inside `response.status` first, then top-level `status`.
        """
        if not isinstance(res, dict):
            return ''
        payload = res.get('response') or {}
        status = (payload or {}).get('status') or res.get('status') or ''
        return str(status).upper()

    def snappay_verify(self, payment_token, tx):

        self.ensure_one()

        def _verify_call():
            try:
                res = self._snappay_request(
                    '/api/online/payment/v1/verify',
                    json_body={'paymentToken': payment_token},
                    method='POST',
                    timeout=60,
                )
                return _jsonify_response(res)
            except requests.exceptions.Timeout:
                _logger.warning("SnappPay verify timeout for token %s", payment_token)
                return {'error': 'timeout'}
            except requests.RequestException:
                _logger.exception("SnappPay verify request error")
                return {'error': 'request_error'}

        # 1) تلاش اول verify
        verify_payload = _verify_call()

        # اگر explicit موفق (successful=True) بود → برو برای settle
        if _is_success_flag(verify_payload, default=False):
            settle_payload = self.snappay_settle(payment_token, tx, timeout_sec=30)
            return _jsonify_response(settle_payload)

        # اگر timeout یا unsuccessful → وضعیت را چک کن
        status_payload = self.snappay_status(payment_token) or {}
        status = _normalize_status(status_payload)

        if status in VERIFY_OK_STATES:
            # قابل ستل‌کردن است
            settle_payload = self.snappay_settle(payment_token, tx, timeout_sec=30)
            return _jsonify_response(settle_payload)

        if status in PENDING_STATES:
            # یک بک‌آف کوتاه: دوباره verify
            def _verify_again():
                return _verify_call()

            verify_payload = _poll_once_then_backoff(_verify_again, max_attempts=2, wait_seconds=3)
            if _is_success_flag(verify_payload, default=False):
                settle_payload = self.snappay_settle(payment_token, tx, timeout_sec=30)
                return _jsonify_response(settle_payload)
            # همچنان نه؟ آخرین وضعیت را برگردان
            return _jsonify_response(verify_payload or status_payload)

        # در غیر اینصورت همون status را برگردون
        return _jsonify_response(status_payload)

    def snappay_settle(self, payment_token, tx, timeout_sec=30):

        self.ensure_one()

        def _settle_call():
            return self._snappay_request(
                '/api/online/payment/v1/settle',
                json_body={'paymentToken': payment_token},
                method='POST',
                timeout=timeout_sec,
            )

        # تلاش اول
        try:
            res = _settle_call()
            payload = _jsonify_response(res)
        except requests.exceptions.Timeout:
            _logger.warning("SnappPay settle timeout for token %s", payment_token)
            # Timeout → وضعیت را چک کن
            status_payload = self.snappay_status(payment_token) or {}
            st = _normalize_status(status_payload)
            if st in VERIFY_OK_STATES:
                # یک تلاش دیگر
                time.sleep(2)
                try:
                    res2 = _settle_call()
                    payload = _jsonify_response(res2)
                except requests.exceptions.Timeout:
                    return _jsonify_response(status_payload)
            elif st in SETTLED_STATES:
                # بالادست ستل شده → موفق
                payload = _jsonify_response(status_payload)
            else:
                return _jsonify_response(status_payload)
        except requests.RequestException:
            _logger.exception("SnappPay settle request error")
            return {'error': 'request_error'}

        # اینجا پاسخ داریم؛ بررسی موفقیت
        ok = _is_success_flag(payload, default=False)
        if not ok:
            # نامشخص → وضعیت را چک کن
            status_payload = self.snappay_status(payment_token) or {}
            st = _normalize_status(status_payload)
            if st in VERIFY_OK_STATES:
                # یک بار دیگر settle
                time.sleep(2)
                try:
                    res3 = _settle_call()
                    payload = _jsonify_response(res3)
                    ok = _is_success_flag(payload, default=False)
                except requests.exceptions.Timeout:
                    # اگر باز هم timeout، آخرین وضعیت را برگردان
                    return _jsonify_response(status_payload)
            elif st in SETTLED_STATES:
                payload = _jsonify_response(status_payload)
                ok = True

        # ست کردن وضعیت تراکنش/سفارش
        if ok:
            try:
                tx._set_done()
            except Exception:
                _logger.exception("Failed to set tx done for %s", tx)
            _safe_store_settle_status(tx.sudo().sale_order_ids, payload)
        else:
            # تصمیم‌گیری با شماست: اینجا set_canceled نکن؛ چون ممکنه قابل پیگیری باشد
            _safe_store_settle_status(tx.sudo().sale_order_ids, payload)

        return payload

    # def snappay_verify(self, payment_token,tx):
    #     self.ensure_one()
    #     token = self._snappay_get_jwt(force_refresh=True)
    #     headers = {
    #         'Authorization': f'Bearer {token}',
    #         'Content-Type': 'application/json',
    #         'Accept': 'application/json',
    #     }
    #     url = self._snappay_api_url("/api/online/payment/v1/verify")
    #     res = requests.post(url, headers=headers, json={'paymentToken': payment_token}, timeout=60)
    #     if bool(res.get('successful', False)):
    #         self.snappay_settle(payment_token,tx, timeout_sec=30)
    #         return res
    #
    #     status_res = self.snappay_status(payment_token)
    #     st = self._snappay_extract_status(status_res)
    #     if st in {'VERIFY', 'VERIFIED', 'VERIFY_SUCCESS'}:
    #             settle_res = self.snappay_settle(payment_token,tx, timeout_sec=30)
    #             if bool(settle_res.get('successful', False)):
    #                 return settle_res
    #
    #     elif st in {'PENDING', 'VERIFY_PENDING'}:
    #         time.sleep(5)
    #         res = requests.post(url, headers=headers, json={'paymentToken': payment_token}, timeout=60)
    #         if bool(res.get('successful', False)):
    #             self.snappay_settle(payment_token, tx, timeout_sec=60)
    #             tx._set_done()
    #             return res
    #         else:
    #             tx._set_canceled()
    #
    #     else:
    #
    #         return status_res
    # def snappay_settle(self, payment_token ,tx, timeout_sec=30):
    #
    #     self.ensure_one()
    #     try:
    #         res = self._snappay_request(
    #             '/api/online/payment/v1/settle',
    #             json_body={'paymentToken': payment_token},
    #             method='POST',
    #             timeout=timeout_sec,
    #         )
    #         tx._set_done()
    #         tx.sudo().sale_order_ids.settle_status = res
    #
    #     except requests.exceptions.Timeout:
    #         # Timeout → look at status
    #         status_res = self.snappay_status(payment_token)
    #         st = self._snappay_extract_status(status_res)
    #         if st in {'VERIFY', 'VERIFIED', 'VERIFY_SUCCESS'}:
    #             # Try one more settle
    #             time.sleep(2)
    #             try:
    #                res = self._snappay_request(
    #                     '/api/online/payment/v1/settle',
    #                     json_body={'paymentToken': payment_token},
    #                     method='POST',
    #                     timeout=timeout_sec,
    #                 )
    #                tx.sudo().sale_order_ids.settle_status = res
    #                tx._set_done()
    #             except requests.exceptions.Timeout:
    #                 return status_res
    #         elif st in {'SETTLE', 'SETTLED', 'SETTLED_SUCCESS'}:
    #             # Already settled upstream → accept as success
    #             return status_res
    #         else:
    #             return status_res
    #     else:
    #         # We got a response, but it could be unsuccessful/False
    #         ok = False
    #         if isinstance(res, dict):
    #             ok = bool(res.get('successful', True))  # some endpoints don't return this flag
    #         if ok:
    #             return res
    #         # Not clearly successful → check status
    #         status_res = self.snappay_status(payment_token)
    #         st = self._snappay_extract_status(status_res)
    #         if st in {'VERIFY', 'VERIFIED', 'VERIFY_SUCCESS'}:
    #             # Try one more settle
    #             time.sleep(2)
    #
    #             res = self._snappay_request(
    #                 '/api/online/payment/v1/settle',
    #                 json_body={'paymentToken': payment_token},
    #                 method='POST',
    #                 timeout=timeout_sec,
    #             )
    #             tx.sudo().sale_order_ids.settle_status = res
    #             tx._set_done()
    #         elif st in {'SETTLE', 'SETTLED', 'SETTLED_SUCCESS'}:
    #             return status_res
    #         return res

    def snappay_status(self, payment_token):
        """GET /api/online/payment/v1/status?paymentToken=..."""
        self.ensure_one()
        # برای سادگی، از _snappay_request(GET) استفاده می‌کنیم (بدون query). این یکی را مستقیم call می‌کنیم.
        token = self._snappay_get_jwt()
        headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
        url = self._snappay_api_url(f"/api/online/payment/v1/status?paymentToken={payment_token}")
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 401:
                token = self._snappay_get_jwt(force_refresh=True)
                headers['Authorization'] = f'Bearer {token}'
                resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            _logger.exception("SnappPay status call failed")
            raise UserError(_("SnappPay status call failed: %s") % e)

    def snappay_check_installment_eligibility(self, amount):
        self.ensure_one()
        token = self._snappay_get_jwt(force_refresh=True)
        url = f"{self.snappay_base_url}/api/online/offer/v1/eligible"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        params = {"amount": int(amount)*10}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            data = response.json()
            if not response.ok:
                return False
        except Exception as e:
            return False
        success = bool(data.get("successful"))
        response = data.get("response", {}) or {}
        eligible = response.get("eligible", False)

        if success and eligible:
            self.snappay_title_message = response.get("title_message") or self.name
            self.snappay_description_message = response.get("description") or ""
            return True
        return False

    @api.model
    def _get_compatible_providers(
            self, company_id, partner_id, amount, currency_id=None, force_tokenization=False,
            is_express_checkout=False, is_validation=False, report=None, **kwargs
    ):
        providers = super()._get_compatible_providers(
            company_id, partner_id, amount, currency_id=currency_id,
            force_tokenization=force_tokenization, is_express_checkout=is_express_checkout,
            is_validation=is_validation, report=report, **kwargs
        )

        if is_validation or not amount:
            return providers

        snappay_providers = providers.filtered(lambda p: p.code == 'snappay' and p.state in ('enabled', 'test'))
        if not snappay_providers:
            return providers

        to_exclude = self.env['payment.provider']
        for prov in snappay_providers:
            try:
                if not prov.snappay_check_installment_eligibility(amount):
                    to_exclude |= prov
            except Exception:
                to_exclude |= prov

        if to_exclude:

            providers -= to_exclude

        return providers

    def _compute_snappay_dynamic_texts(self):
        for p in self:
            p.snappay_title_message = False
            p.snappay_description_message = False





