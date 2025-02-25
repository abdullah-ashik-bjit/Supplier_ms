from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    address_home_id = fields.Many2one('res.partner', string="Related Vendor")
