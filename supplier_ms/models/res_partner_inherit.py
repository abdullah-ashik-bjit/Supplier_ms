from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SupplierData(models.Model):
    _inherit = 'res.partner'
    _description = 'Supplier Registration'

    # Make fields required only for suppliers using required_if_supplier decorator
    @api.depends('supplier_rank')
    def _compute_field_required(self):
        for record in self:
            record.is_supplier_required = record.supplier_rank > 0

    is_supplier_required = fields.Boolean(compute='_compute_field_required')

    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('both', 'Customer and Vendor')
    ], string='Partner Type', default='customer')

    # Company Information
    company_registered_address = fields.Text(string='Registered Address')
    company_alternate_address = fields.Text(string='Alternate Address')
    company_type_category = fields.Selection([
        ('llc', 'LLC'),
        ('corporation', 'Corporation'),
        ('partnership', 'Partnership'),
        ('sole_proprietorship', 'Sole Proprietorship'),
        ('cooperative', 'Cooperative')
    ], string='Company Category')
    trade_license_number = fields.Char(string='Trade License Number')
    tax_identification_number = fields.Char(string='Tax ID Number')
    commencement_date = fields.Date(string='Commencement Date')
    expiry_date = fields.Date(string='Expiry Date')

    # Certification Fields
    certificate_name = fields.Char(string="Certification Name")
    certificate_number = fields.Char(string="Certificate Number")
    certifying_body = fields.Char(string="Certifying Body")
    award_date = fields.Date(string="Award Date")
    cert_expiry_date = fields.Date(string="Expiry Date")

    # Contact Fields
    primary_contact_id = fields.Many2one('hr.employee', string="Primary Contact")
    authorized_contact_id = fields.Many2one('hr.employee', string="Authorized Contact")
    finance_contact_id = fields.Many2one('hr.employee', string="Finance Contact")

    # Document Fields - All with attachment=True
    trade_license_business_registration = fields.Binary(
        string="Trade License/Business Registration",
        attachment=True
    )
    certificate_of_incorporation = fields.Binary(
        string="Certificate of Incorporation",
        attachment=True
    )
    certificate_of_good_standing = fields.Binary(
        string="Certificate of Good Standing",
        attachment=True
    )
    establishment_card = fields.Binary(
        string="Establishment Card",
        attachment=True
    )
    vat_tax_certificate = fields.Binary(
        string="VAT/Tax Certificate",
        attachment=True
    )
    memorandum_of_association = fields.Binary(
        string="Memorandum of Association",
        attachment=True
    )
    identification_document_for_authorized_person = fields.Binary(
        string="Identification Document",
        attachment=True
    )
    bank_letter_indicating_bank_account = fields.Binary(
        string="Bank Letter",
        attachment=True
    )
    past_2_years_audited_financial_statements = fields.Binary(
        string="Financial Statements",
        attachment=True
    )
    other_certifications = fields.Binary(
        string="Other Certifications",
        attachment=True
    )

    # Signatory Fields - Make required only for suppliers
    signatory_name = fields.Char(
        string="Name of Signatory", 
        required=False  # Remove the always required
    )
    authorized_signatory = fields.Char(
        string="Authorized Signatory", 
        required=False  # Remove the always required
    )
    company_stamp = fields.Binary(
        string="Company Stamp & Date", 
        required=False  # Remove the always required
    )

    client_reference_ids = fields.One2many('supplier.client.reference', 'supplier_id', string="Client References")

    @api.constrains('supplier_rank', 'signatory_name', 'authorized_signatory', 'company_stamp')
    def _check_required_fields_for_supplier(self):
        for record in self:
            if record.supplier_rank > 0:  # Only check for suppliers
                if not record.signatory_name:
                    raise ValidationError("Name of Signatory is required for suppliers.")
                if not record.authorized_signatory:
                    raise ValidationError("Authorized Signatory is required for suppliers.")
                if not record.company_stamp:
                    raise ValidationError("Company Stamp is required for suppliers.")

    @api.constrains("expiry_date")
    def _check_expiry_date(self):
        for record in self:
            if record.supplier_rank > 0 and record.expiry_date and record.expiry_date < fields.Date.today():
                raise ValidationError("Expired certifications cannot be added.")

    @api.model
    def create(self, vals):
        if vals.get('partner_type') == 'vendor' and vals.get('company_name'):
            vals['name'] = vals['company_name']
        return super(SupplierData, self).create(vals)

    @api.onchange('company_name', 'partner_type')
    def _onchange_company_name(self):
        if self.partner_type == 'vendor' and self.company_name:
            self.name = self.company_name