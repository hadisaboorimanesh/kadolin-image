# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _


class artaradServerActions(models.Model):
    _name = 'ir.actions.server'
    _inherit = ['ir.actions.server']

    @api.constrains('state', 'model_id')
    def _check_sms_capability(self):
        pass

    def _run_action_sms_multi(self, eval_context=None):
        if self.sms_template_id.mobile_to:
            if not self.sms_template_id or self._is_recompute():
                return False

            records = eval_context.get('records') or eval_context.get('record')
            if not records:
                return False

            if self.model_id.is_mail_thread:
                subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')
                messages = self.env['mail.message']
                for record in records:
                    messages |= record._message_sms(
                        self.sms_template_id._render_field("body", [record.id], compute_lang=True)[record.id],
                        subtype_id=subtype_id,
                        sms_numbers=[self.sms_template_id._render_field("mobile_to", [record.id], compute_lang=True)[record.id]])
            else:
                sms_provider_id = self.env["artarad.sms.provider.setting"].search([], order="sequence asc", limit=1)
                for record in records:
                    sms_provider_id.send_sms(self.sms_template_id._render_field("mobile_to", [record.id], compute_lang=True)[record.id],
                                             self.sms_template_id._render_field("body", [record.id], compute_lang=True)[record.id])
            return False
        else:
            return super(artaradServerActions, self)._run_action_sms_multi(eval_context)