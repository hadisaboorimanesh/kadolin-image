# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _


class artaradResPartner(models.Model):
    _inherit = "res.partner"
    
    # additional fields
    authentication_state = fields.Selection([('not_authenticated', 'Not Authenticated'), ('authenticated', 'Authenticated')], string="Authentication State", required=True, default='not_authenticated', tracking=True)
    national_number = fields.Char()
    code_atba = fields.Char(string="کد اتباع")
    registeration_number = fields.Char(string="Registeration Number")
    economic_number = fields.Char(string="Economic Number")
    zone_id =fields.Many2one('artarad.res.zone',string="Zone")



    def _check_national_number_validity_as_person(self, number):
        if len(number) == 10:
            # calculate sumation & it's reminder
            sumation = 0
            for i in range(len(number) - 1):
                sumation += int(number[i])*(len(number) - i)
            reminder = sumation%11

            if reminder < 2 and reminder == int(number[9]):
                return True
            elif (11-reminder) == int(number[9]):
                return True

        return False

    def _check_national_number_validity_as_company(self, number):
        if len(number) == 11:
            multiples = [29, 27, 23, 19, 17, 29, 27, 23, 19, 17]
            # calculate sumation & it's reminder
            sumation = 0
            for i in range(len(number) - 1):
                sumation += (int(number[i]) + int(number[9]) + 2)*(multiples[i])
            reminder = sumation%11
            if reminder == 10:
                reminder = 0
            # calculate_is_valid
            if reminder == int(number[10]):
                return True
        return False

    @api.constrains("national_number")
    def _check_national_number_validity(self):
        if self.env.company.numbers_validity_check:
            for rec in self:
                if rec.national_number not in [False, '']:
                    if rec.company_type == 'person':
                        is_valid = rec._check_national_number_validity_as_person(rec.national_number)
                    else:
                        is_valid = rec._check_national_number_validity_as_company(rec.national_number)
                    if not is_valid:
                        raise exceptions.ValidationError(_("Customer National Number/ID is not valid!"))
            
    @api.constrains("national_number")
    def _check_national_number_uniqueness(self):
        if self.env.company.numbers_uniqueness_check:
            for rec in self:
                if rec.national_number not in [False, '']:
                    customers = self.env['res.partner'].search([('national_number', '=', rec.national_number)])
                    if len(customers) > 1:
                        raise exceptions.ValidationError(_("Customer National Number/ID is not unique!"))