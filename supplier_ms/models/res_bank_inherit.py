from odoo import api, fields, models

class BankExtended(models.Model):
    _inherit = 'res.bank'
    _description = 'Bank Extended'

    bank_swift_code = fields.Char(string='Bank Swift Code')
