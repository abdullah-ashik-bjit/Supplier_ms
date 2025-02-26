# -*- coding: utf-8 -*-
import base64

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import http, _
import string
import secrets
import logging
from ..data.mail_utils import (
    send_supplier_review_approval,
    send_supplier_final_approval,
    send_supplier_blacklist_notification,
    send_supplier_registration_notification,
    send_final_approval_notification,
    send_final_rejection_notification
)
_logger = logging.getLogger(__name__)

class SupplierApplication(models.Model):
    _name = 'supplier.application'
    _description = 'Supplier Application'
    _rec_name = 'company_name'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Add this field to track the created vendor
    vendor_id = fields.Many2one('res.partner', string='Created Vendor', readonly=True)

    # Company Information
    company_name = fields.Char(string="Company Name", required=True, tracking=True)
    company_address = fields.Text(string="Company Address", required=True)
    email = fields.Char(string="Company Email", required=True, tracking=True)
    company_type = fields.Selection([
        ('llc', 'LLC'),
        ('corporation', 'Corporation'),
        ('partnership', 'Partnership'),
        ('sole_proprietor', 'Sole Proprietor')
    ], string="Company Type", required=True)
    company_logo = fields.Binary(
        string='Company Logo',
        attachment=True,  # Store as attachment
        help="Upload company logo here"
    )
    trade_license_number = fields.Char(string="Trade License Number")
    tax_identification_number = fields.Char(string="Tax Identification Number (TIN)")
    commencement_date = fields.Date(string="Commencement Date")
    expiry_date = fields.Date(string="Expiry Date")

    # Primary Contact
    primary_contact_name = fields.Char(string="Primary Contact Name", required=True)
    primary_contact_email = fields.Char(string="Primary Contact Email", required=True)
    primary_contact_phone = fields.Char(string="Primary Contact Phone", required=True)
    primary_contact_address = fields.Text(string="Primary Contact Address")

    # Finance Contact
    finance_contact_name = fields.Char(string="Finance Contact Name")
    finance_contact_email = fields.Char(string="Finance Contact Email")
    finance_contact_phone = fields.Char(string="Finance Contact Phone")
    finance_contact_address = fields.Text(string="Finance Contact Address")

    # Authorized Contact
    authorized_contact_name = fields.Char(string="Authorized Contact Name", required=True)
    authorized_contact_email = fields.Char(string="Authorized Contact Email", required=True)
    authorized_contact_phone = fields.Char(string="Authorized Contact Phone", required=True)
    authorized_contact_address = fields.Text(string="Authorized Contact Address")

    # Bank Information
    bank_name = fields.Char(string="Bank Name", required=True)
    bank_address = fields.Text(string="Bank Address", required=True)
    bank_swift_code = fields.Char(string="SWIFT Code", required=True)
    bank_account_name = fields.Char(string="Bank Account Name", required=True)
    bank_account_number = fields.Char(string="Bank Account Number", required=True)
    iban = fields.Char(string="IBAN")

    # Client References
    client_1_name = fields.Char(string="Client 1 Name")
    client_1_email = fields.Char(string="Client 1 Email")
    client_1_phone = fields.Char(string="Client 1 Phone")
    client_1_address = fields.Text(string="Client 1 Address")

    client_2_name = fields.Char(string="Client 2 Name")
    client_2_email = fields.Char(string="Client 2 Email")
    client_2_phone = fields.Char(string="Client 2 Phone")
    client_2_address = fields.Text(string="Client 2 Address")

    client_3_name = fields.Char(string="Client 3 Name")
    client_3_email = fields.Char(string="Client 3 Email")
    client_3_phone = fields.Char(string="Client 3 Phone")
    client_3_address = fields.Text(string="Client 3 Address")

    client_4_name = fields.Char(string="Client 4 Name")
    client_4_email = fields.Char(string="Client 4 Email")
    client_4_phone = fields.Char(string="Client 4 Phone")
    client_4_address = fields.Text(string="Client 4 Address")

    client_5_name = fields.Char(string="Client 5 Name")
    client_5_email = fields.Char(string="Client 5 Email")
    client_5_phone = fields.Char(string="Client 5 Phone")
    client_5_address = fields.Text(string="Client 5 Address")


    # Certifications
    certificate_name = fields.Char(string="Certification Name", required=True)
    certificate_number = fields.Char(string="Certificate Number")
    certifying_body = fields.Char(string="Certifying Body", required=True)
    award_date = fields.Date(string="Award Date", required=True)
    cert_expiry_date = fields.Date(string="Expiry Date", required=True)

    # Document Attachments
    trade_license = fields.Binary(
        string="Trade License / Business Registration", 
        attachment=True,
        required=True
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
        string="VAT / Tax Certificate",
        attachment=True
    )
    memorandum_of_association = fields.Binary(
        string="Memorandum of Association / Power of Attorney",
        attachment=True
    )
    identification_document = fields.Binary(
        string="Identification Document for Authorized Person",
        attachment=True
    )
    bank_letter = fields.Binary(
        string="Bank Letter indicating Bank Account Information",
        attachment=True
    )
    financial_statements = fields.Binary(
        string="Past 2 years of Audited Financial Statements",
        attachment=True
    )
    other_certifications = fields.Binary(
        string="Other Certification / Accreditations",
        attachment=True
    )

    # Declaration
    declaration_confirm = fields.Boolean(string="Declaration Confirmation", required=True)
    signatory_name = fields.Char(string="Name of Signatory", required=True)
    authorized_signatory = fields.Char(string="Authorized Signatory", required=True)
    company_stamp = fields.Binary(string="Company Stamp & Date", required=True)

    # -----------------------------
    # Review & Approval Process
    # -----------------------------
    state = fields.Selection([
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('blacklisted', 'Blacklisted')
    ], string="Status", default='submitted', tracking=True)

    reviewer_comments = fields.Text(string="Reviewer Comments")
    approver_comments = fields.Text(string="Approver Comments")

    # Add these fields if not already present
    blacklist_date = fields.Datetime(string='Blacklist Date', readonly=True)

    @api.constrains('email', 'primary_contact_email', 'authorized_contact_email')
    def _check_unique_email(self):
        """Ensure that emails are unique and valid"""
        for record in self:
            existing = self.search([
                '|', ('primary_contact_email', '=', record.primary_contact_email),
                     ('authorized_contact_email', '=', record.authorized_contact_email)
            ], limit=1)
            if existing and existing.id != record.id:
                raise ValidationError("The email address is already registered.")

    @api.constrains('tax_identification_number', 'trade_license_number')
    def _check_tax_and_license(self):
        """Validate Tax Identification Number and Trade License Number"""
        for record in self:
            if record.tax_identification_number and (
                len(record.tax_identification_number) != 16 or not record.tax_identification_number.isdigit()
            ):
                raise ValidationError("Tax Identification Number must be exactly 16 digits.")

            if record.trade_license_number and (
                len(record.trade_license_number) < 8 or not record.trade_license_number.isalnum()
            ):
                raise ValidationError("Trade License Number must be alphanumeric (8-20 characters).")

    @api.constrains('trade_license', 'certificate_of_incorporation', 'vat_tax_certificate', 'financial_statements')
    def _validate_file_size(self):
        """Ensure that uploaded files are not greater than 1MB"""
        max_size = 1 * 1024 * 1024  # 1MB in bytes
        file_fields = ['trade_license', 'certificate_of_incorporation', 'vat_tax_certificate', 'financial_statements']

        for record in self:
            for field in file_fields:
                file_data = getattr(record, field)
                if file_data and len(file_data.decode('utf-8')) > max_size:
                    raise ValidationError(f"The file {field.replace('_', ' ')} exceeds the maximum size limit of 1MB.")

    # -------------------------------
    # 🔹 Review & Approval Actions
    # -------------------------------

    def action_submit(self):
        """ Submit application for review """
        self.write({'state': 'submitted'})

    def action_review_approve(self):
        """Reviewer Approves, moves to Approver for final decision"""
        try:
            self.write({'state': 'reviewed'})
            
            approver_group = self.env.ref('supplier_ms.group_approver')
            approvers = approver_group.users

            if not approvers:
                _logger.warning("No approvers found")
                return

            for approver in approvers:
                send_supplier_review_approval(self.env, self, approver)

        except Exception as e:
            _logger.error(f"Failed to process review approval: {str(e)}")
            raise UserError(_("Failed to process review approval: %s") % str(e))

    def action_review_reject(self):
        """Reviewer Rejects the application"""
        if not self.reviewer_comments:
            raise UserError(_("Please provide a reason for rejection."))
        
        self.write({'state': 'rejected'})
        send_final_rejection_notification(self.env, self)

    def action_review_blacklist(self):
        """Blacklist the supplier application"""
        if not self.reviewer_comments:
            raise UserError(_("Please provide a reason for blacklisting."))

        try:
            if not self.email:
                raise UserError(_("Cannot blacklist: No email address found."))

            self.env['mail.blacklist'].sudo().create({
                'email': self.email,
                'reason': self.reviewer_comments,
            })

            self.write({
                'state': 'blacklisted',
                'blacklist_date': fields.Datetime.now(),
            })

            send_supplier_blacklist_notification(self.env, self)

        except Exception as e:
            _logger.error(f"Failed to blacklist application: {str(e)}")
            raise UserError(_("Failed to blacklist application: %s") % str(e))

    def action_final_approve(self):
        """Final approval of supplier application"""
        try:
            self.ensure_one()

            if not self.exists():
                raise UserError(_("The supplier application no longer exists."))

            # Create vendor using the optimized create_vendor method
            vendor = self.create_vendor()
            if not vendor:
                raise UserError(_("Failed to create vendor record."))

            # Update application status
            self.write({
                'state': 'approved',
            })

            vendor.sudo().write({
                'supplier_rank': 1,
            })

            # Add this temporarily to check the created records
            _logger.info(f"Created vendor: {vendor.name}, is_company: {vendor.is_company}")

            return True

        except Exception as e:
            _logger.error(f"Final approval failed: {str(e)}")
            raise UserError(_("Failed to approve supplier: %s") % str(e))

    def action_final_reject(self):
        """Final Rejection"""
        if not self.approver_comments:
            raise UserError(_("Please provide a reason for final rejection."))
        
        try:
            self.write({'state': 'rejected'})
            
            # Send rejection notification
            template = self.env.ref('supplier_ms.email_template_final_rejection')
            if template:
                template.send_mail(
                    self.id,
                    raise_exception=True
                )
                _logger.info(f"Final rejection notification sent to: {self.email}")


        except Exception as e:
            _logger.error(f"Failed to reject application: {str(e)}")
            raise UserError(_("Failed to reject application: %s") % str(e))

    # -------------------------------
    #  Vendor Creation
    # -------------------------------

    def create_vendor(self):
        """ Creates a Vendor in Odoo upon approval """

        try:
            # Map the company_type to company_type_category
            company_type_mapping = {
                'llc': 'company',
                'corporation': 'company',
                'partnership': 'company',
                'sole_proprietor': 'person'
            }

            # Ensure company_type is mapped correctly
            company_type_category = company_type_mapping.get(self.company_type, 'company')

            # Create vendor record
            vendor_vals = {
                # Basic Information
                'name': self.company_name,
                'company_name': self.company_name,
                'company_type': 'company',
                'is_company': True,
                
                # Address Fields
                'street': self.company_address,  # Main address
                'street2': self.company_address,  # Alternate address
                'vat': self.tax_identification_number,  # VAT/Tax ID
                
                # Contact Information
                'email': self.email,
                'website': self.website if hasattr(self, 'website') else False,
                'phone': self.phone if hasattr(self, 'phone') else False,
                
                # Image
                'image_1920': self.company_logo,
                
                # Partner Type
                'partner_type': 'vendor',
                
                # Custom Fields
                'company_type_category': self.company_type,
                'trade_license_number': self.trade_license_number,
                'commencement_date': self.commencement_date,
                'expiry_date': self.expiry_date,
                'certificate_name': self.certificate_name,
                'certificate_number': self.certificate_number,
                'certifying_body': self.certifying_body,
                'award_date': self.award_date,
                'cert_expiry_date': self.cert_expiry_date,
                'signatory_name': self.signatory_name,
                'authorized_signatory': self.authorized_signatory,
                'company_stamp': self.company_stamp,
            }

            # Add company logo if exists
            if self.company_logo:
                vendor_vals['image_1920'] = self.company_logo

            vendor = self.env['res.partner'].with_context(default_supplier_rank=1).create(vendor_vals)

            # Create child contact for primary contact if needed
            if self.primary_contact_name:
                self.env['res.partner'].create({
                    'name': self.primary_contact_name,
                    'email': self.primary_contact_email,
                    'phone': self.primary_contact_phone,
                    'parent_id': vendor.id,  # Link to company
                    'type': 'contact',  # Set as contact type
                    'company_type': 'person'  # Set as individual
                })

            # Update application status
            self.write({
                'vendor_id': vendor.id
            })

            # Update supplier_rank explicitly
            vendor.write({
                'supplier_rank': 1,  # This will ensure it appears in vendor bills
            })

            if self.finance_contact_name:
                self.env['res.partner'].create({
                    'name': self.finance_contact_name,
                    'email': self.finance_contact_email,
                    'phone': self.finance_contact_phone,
                    'parent_id': vendor.id,  # Link to company
                    'type': 'contact',  # Set as contact type
                    'company_type': 'person'  # Set as individual
                })

            if self.authorized_contact_name:
                self.env['res.partner'].create({
                    'name': self.authorized_contact_name,
                    'email': self.authorized_contact_email,
                    'phone': self.authorized_contact_phone,
                    'parent_id': vendor.id,  # Link to company
                    'type': 'contact',  # Set as contact type
                    'company_type': 'person'  # Set as individual
                })

            # Store other details
            self._store_bank_details(vendor)
            # self._store_contact_persons(vendor)
            self._store_client_references(vendor)
            self._store_supplier_documents(vendor)
            self._create_supplier_user(vendor)

            _logger.info(f"Created vendor: {vendor.name}, is_company: {vendor.is_company}")
            return vendor

        except Exception as e:
            _logger.error(f"Vendor creation failed: {str(e)}")
            raise UserError(_("Failed to create vendor: %s") % str(e))



    def _store_bank_details(self, vendor):
        """ Stores Bank Details and Links to Vendor """

        # Search for the bank based on the bank name (if it already exists)
        bank = self.env['res.bank'].sudo().search([('name', '=', self.bank_name)], limit=1)

        # If the bank does not exist, create a new one
        if not bank:
            bank = self.env['res.bank'].sudo().create({
                'name': self.bank_name,
                'bic': self.bank_swift_code
            })

        # Create the bank account link with the vendor
        self.env['res.partner.bank'].sudo().create({
            'partner_id': vendor.id,  # Link the bank account to the vendor
            'bank_id': bank.id,  # Bank ID (from res.bank)
            'acc_number': self.bank_account_number,
            'iban': self.iban,
            'address': self.bank_address
        })

    # def _store_contact_persons(self, vendor):
    #     """ Creates Primary and Authorized Contact Persons """
    #
    #     # Data for primary and authorized contact
    #     contact_vals = {
    #         'primary_contact_id': {
    #             'name': self.primary_contact_name,
    #             'work_email': self.primary_contact_email,
    #             'mobile_phone': self.primary_contact_phone,
    #         },
    #         'authorized_contact_id': {
    #             'name': self.authorized_contact_name,
    #             'work_email': self.authorized_contact_email,
    #             'mobile_phone': self.authorized_contact_phone,
    #         },
    #         'finance_contact_id': {
    #             'name': self.finance_contact_name,
    #             'work_email': self.finance_contact_email,
    #             'mobile_phone': self.finance_contact_phone,
    #
    #         },
    #     }
    #
    #     # Create the contacts and link them to the vendor
    #     for field, data in contact_vals.items():
    #         if data['name']:  # Ensure name exists for contact creation
    #             employee = self.env['hr.employee'].sudo().create({**data, 'address_home_id': vendor.id})
    #             vendor.write({field: employee.id})

    def _store_client_references(self, vendor):
        """ Stores Client References for the Vendor """
        client_fields = [
            ('client_1_name', 'client_1_email', 'client_1_phone', 'client_1_address'),
            ('client_2_name', 'client_2_email', 'client_2_phone', 'client_2_address'),
            ('client_3_name', 'client_3_email', 'client_3_phone', 'client_3_address'),
            ('client_4_name', 'client_4_email', 'client_4_phone', 'client_4_address'),
            ('client_5_name', 'client_5_email', 'client_5_phone', 'client_5_address'),
        ]

        # Generate client reference data from the form fields
        references = []
        for fields in client_fields:
            if getattr(self, fields[0]):  # If client name exists
                references.append({
                    'supplier_id': vendor.id,
                    'client_name': getattr(self, fields[0]),
                    'client_email': getattr(self, fields[1]),
                    'client_phone': getattr(self, fields[2]),
                    'client_address': getattr(self, fields[3])
                })

        # Create client references
        if references:
            self.env['supplier.client.reference'].sudo().create(references)

    def _store_supplier_documents(self, vendor):
        """Store supplier documents in vendor record"""
        try:
            document_vals = {
                'trade_license_business_registration': self.trade_license,
                'certificate_of_incorporation': self.certificate_of_incorporation,
                'certificate_of_good_standing': self.certificate_of_good_standing,
                'establishment_card': self.establishment_card,
                'vat_tax_certificate': self.vat_tax_certificate,
                'memorandum_of_association': self.memorandum_of_association,
                'identification_document_for_authorized_person': self.identification_document,
                'bank_letter_indicating_bank_account': self.bank_letter,
                'past_2_years_audited_financial_statements': self.financial_statements,
                'other_certifications': self.other_certifications,
                'company_stamp': self.company_stamp
            }

            # Update vendor with documents
            vendor.sudo().write(document_vals)

        except Exception as e:
            _logger.error(f"Error storing supplier documents: {str(e)}")
            raise UserError(_("Failed to store supplier documents: %s") % str(e))

    def _create_supplier_user(self, vendor):
        """Creates a Portal User for the Vendor"""
        try:
            # Check if user already exists
            existing_user = self.env['res.users'].sudo().search([
                ('login', '=', self.email)
            ], limit=1)

            if existing_user:
                raise UserError(_("A user with this email already exists."))

            # Generate a secure random password
            random_password = self._generate_secure_password()

            # Prepare user values
            user_vals = {
                'name': self.company_name,
                'login': self.email,
                'email': self.email,
                'partner_id': vendor.id,
                'password': random_password,
                'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
                'active': True,
                'notification_type': 'email',
            }

            # Create user with all notifications disabled
            user = self.env['res.users'].sudo().with_context(
                no_reset_password=True,  # Prevent reset password email
                no_portal_welcome=True,  # Prevent portal welcome email
                create_user=True,  # Indicate this is user creation
                password_reset=False,  # Prevent password reset notification
                signup_valid=False,  # Prevent signup validation
                mail_create_nosubscribe=True  # Prevent auto subscription to messages
            ).create(user_vals)

            if not user:
                raise UserError(_("Failed to create user record"))

            # Send our custom confirmation email
            self._send_vendor_confirmation_email(random_password)

            return user

        except Exception as e:
            _logger.error(f"Failed to create supplier user: {str(e)}")
            if 'duplicate key value violates unique constraint' in str(e):
                raise UserError(_("A user with this email already exists."))
            raise UserError(_("Failed to create supplier user account: %s") % str(e))




    def _generate_secure_password(self, length=12):
        """ Generates a Secure Random Password """
        return ''.join(secrets.choice(string.ascii_letters + string.digits + "!@#$%^&*()?") for _ in range(length))

    def _send_vendor_confirmation_email(self, password):
        """Send confirmation email to approved vendor"""
        send_supplier_final_approval(self.env, self, password)

    def _notify_approvers(self):
        """Send notification to approvers for final review"""
        try:
            approver_group = self.env.ref('supplier_ms.group_approver')
            approvers = approver_group.users

            if not approvers:
                _logger.warning("No approvers found")
                return

            for approver in approvers:
                send_final_approval_notification(self.env, self, approver)

        except Exception as e:
            _logger.error(f"Failed to notify approvers: {str(e)}")
            raise UserError(_("Failed to notify approvers: %s") % str(e))

    @api.model
    def create(self, vals):
        """Override create to send notification"""
        record = super(SupplierApplication, self).create(vals)
        
        reviewer_group = self.env.ref('supplier_ms.group_reviewer')
        for reviewer in reviewer_group.users:
            send_supplier_registration_notification(self.env, record, reviewer)
            
        return record