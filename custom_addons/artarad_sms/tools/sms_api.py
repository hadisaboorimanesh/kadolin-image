# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
from odoo.addons.sms.tools.sms_api import SmsApi

import re

def overrided_contact_iap(self, local_endpoint, params, timeout=15):
    results = []
    provider_id = self.env["artarad.sms.provider.setting"].search([], order="sequence asc", limit=1)

    for message in params["messages"]:
        for item in message["numbers"]:
            item["number"] = re.sub("[\s\+\-]", "", item["number"])
            item["number"] = re.sub("^98", "0", item["number"])
            res = provider_id.send_sms(item["number"], message["content"])
            results.append({"uuid": item["uuid"], "state": "success" if res else "error"})

    return results


SmsApi._contact_iap = overrided_contact_iap



