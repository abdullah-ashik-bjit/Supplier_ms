from odoo import fields, models

class MailBlacklistInherit(models.Model):
    _inherit = 'mail.blacklist'
    
    reason = fields.Text(string='Blacklist Reason') 