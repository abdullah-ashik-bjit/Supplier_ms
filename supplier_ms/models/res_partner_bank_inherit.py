from odoo import api, fields, models

class BankAccountExtended(models.Model):
    _inherit = 'res.partner.bank'
    _description = 'Bank Account Extended'

    address = fields.Char(string='Address')
    iban = fields.Char(string='IBAN', help="International Bank Account Number")  # ✅ Added here
