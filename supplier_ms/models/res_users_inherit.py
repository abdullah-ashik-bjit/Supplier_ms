from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    is_supplier = fields.Boolean(string="Is Supplier", default=False)
