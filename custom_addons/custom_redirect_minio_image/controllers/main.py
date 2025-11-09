from odoo import http
from odoo.http import request
from werkzeug.utils import redirect

class MinioImageRedirect(http.Controller):

    @http.route([
        '/web/image/<string:model>/<int:res_id>/<string:field>',
        '/web/image/<string:model>/<int:res_id>/<string:field>/<int:width>x<int:height>',
    ], type='http', auth="public", csrf=False)
    def minio_image_redirect(self, model, res_id, field, width=None, height=None, **kwargs):

        # فقط برای product.template کار کند
        if model == 'product.template' and field in ['image_1920', 'image_1024', 'image_512']:

            attachment = request.env['ir.attachment'].sudo().search([
                ('res_model', '=', model),
                ('res_id', '=', res_id),
                ('name', 'ilike', field),
                ('store_fname', '!=', False)
            ], limit=1)

            if attachment and attachment.store_fname and attachment.store_fname.startswith('minio_bucket://'):
                file_name = attachment.store_fname.replace('minio_bucket://', '')

                # لینک MinIO شما:
                minio_url = f"https://minio.zhaxon.ir/media/{file_name}"

                return redirect(minio_url, code=302)

        # اگر پیدا نشد → برگردد به رفتار پیش فرض Odoo
        return request.env['ir.http'].sudo()._handle_exception(Exception("Use old Odoo image route"))
