from odoo import models, fields


class SupplierClientReference(models.Model):
    _name = "supplier.client.reference"
    _description = "Supplier Client Reference"

    supplier_id = fields.Many2one("res.partner", required=True)
    client_name = fields.Char(required=True)
    client_email = fields.Char()
    client_phone = fields.Char()
    client_address = fields.Char()
