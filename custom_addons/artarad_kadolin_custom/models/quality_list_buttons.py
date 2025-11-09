from odoo import models

class QualityCheck(models.Model):
    _inherit = "quality.check"

    def action_bulk_pass_process(self):
        for rec in self:
            rec.akc_button_pass()


    def action_bulk_fail_process(self):
        for rec in self:
            rec.akc_button_fail()


    def akc_button_pass(self):
        for rec in self:
            for meth in ("action_pass", "button_pass", "do_pass"):
                m = getattr(rec, meth, None)
                if callable(m):
                    m()
                    break
            else:
                if "quality_state" in rec._fields:
                    rec.write({"quality_state": "pass"})
        return True

    def akc_button_fail(self):
        for rec in self:
            for meth in ("action_fail", "button_fail", "do_fail"):
                m = getattr(rec, meth, None)
                if callable(m):
                    m()
                    break
            else:
                if "quality_state" in rec._fields:
                    rec.write({"quality_state": "fail"})
        return True