import base64

from odoo.addons.account.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo import http, _
from odoo.http import request, route
from odoo import fields
from collections import OrderedDict
import logging
from ..data.mail_utils import send_supplier_registration_reviewer_notification

_logger = logging.getLogger(__name__)


class SupplierAuthController(http.Controller):

    # -------------------- OTP Verification --------------------

    @http.route('/supplier/register', type='http', auth="public", website=True)
    def supplier_register(self, **kwargs):
        """Ensure user is not logged in before displaying the Email Verification Form"""
        if request.env.user and request.env.user.id != request.env.ref('base.public_user').id:
            return request.redirect('/my/home')  # Redirect logged-in users to their portal home

        return request.render("supplier_ms.portal_supplier_register")

    @http.route('/supplier/send_otp', type='http', auth="public", methods=['POST'], website=True)
    def send_otp(self, **kwargs):
        """Ensure user is not logged in before sending OTP"""
        if request.env.user and request.env.user.id != request.env.ref('base.public_user').id:
            return request.redirect('/my/home')  # Redirect logged-in users

        email = kwargs.get('email')

        # Check if the email is already registered
        existing_supplier = request.env['res.partner'].sudo().search([('email', '=', email)], limit=1)
        if existing_supplier:
            return request.render("supplier_ms.portal_supplier_register", {
                'error': "Email is already registered."
            })

        # Check if the email is blacklisted using `mail.blacklist`
        is_blacklisted = request.env['mail.blacklist'].sudo().search([('email', '=', email)], limit=1)
        if is_blacklisted:
            return request.render("supplier_ms.portal_supplier_register", {
                'error': "This email is blacklisted."
            })

        # Generate and send OTP
        otp_code = request.env['supplier.otp'].sudo().generate_otp(email)

        return request.render("supplier_ms.portal_supplier_verify_otp", {
            'email': email,
            'success': "OTP has been sent to your email. Please check your inbox"
        })

    @http.route('/supplier/verify_otp', type='http', auth="public", methods=['POST'], website=True)
    def verify_otp(self, **kwargs):
        """Ensure user is not logged in before verifying OTP"""
        if request.env.user and request.env.user.id != request.env.ref('base.public_user').id:
            return request.redirect('/my/home')  # Redirect logged-in users

        email = kwargs.get('email')
        otp = kwargs.get('otp')

        otp_valid = request.env['supplier.otp'].sudo().validate_otp(email, otp)
        if not otp_valid:
            return request.render("supplier_ms.portal_supplier_verify_otp", {
                'email': email,
                'error': "Invalid OTP. Please try again."
            })

        # Redirect to the supplier registration form after successful OTP verification
        return request.redirect('/supplier/register/form?email=' + email)


    # -------------------- Supplier Registration --------------------

    @http.route('/supplier/register/form', type='http', auth="public", website=True)
    def supplier_register_form(self, **kwargs):
        """Render the Supplier Registration Form after OTP Verification"""

        if request.env.user and request.env.user.id != request.env.ref('base.public_user').id:
            return request.redirect('/my/home')  # Redirect logged-in users to their portal home

        email = kwargs.get('email', '').strip()
        if not email:
            return request.redirect('/supplier/register')  # Redirect back if no email
        
        # Initialize form_data dictionary with email
        form_data = {
            'email': email,
            'primary_contact_email': email  # Pre-fill primary contact email with the verified email
        }
        
        return request.render("supplier_ms.portal_supplier_register_form", {
            'email': email,
            'form_data': form_data
        })

    @http.route(['/supplier/register/form/submit'], type='http', auth="public", website=True, csrf=True)
    def register_supplier_form_submit(self, **post):
        error_list = []
        success_list = []
        
        try:
            # Get the uploaded file
            company_logo = request.httprequest.files.get('company_logo')
            # Get all uploaded files
            files = {
                'trade_license': request.httprequest.files.get('trade_license'),
                'certificate_of_incorporation': request.httprequest.files.get('certificate_of_incorporation'),
                'certificate_of_good_standing': request.httprequest.files.get('certificate_of_good_standing'),
                'establishment_card': request.httprequest.files.get('establishment_card'),
                'vat_tax_certificate': request.httprequest.files.get('vat_tax_certificate'),
                'memorandum_of_association': request.httprequest.files.get('memorandum_of_association'),
                'identification_document': request.httprequest.files.get('identification_document'),
                'bank_letter': request.httprequest.files.get('bank_letter'),
                'financial_statements': request.httprequest.files.get('financial_statements'),
                'other_certifications': request.httprequest.files.get('other_certifications'),
                'company_stamp': request.httprequest.files.get('company_stamp')
            }
            
            # Prepare values for supplier application
            vals = {
                'company_name': post.get('company_name'),
                'email': post.get('email'),
                'primary_contact_email': post.get('primary_contact_email'),
                'primary_contact_phone': post.get('primary_contact_phone'),
                'primary_contact_name': post.get('primary_contact_name'),
                'primary_contact_address': post.get('primary_contact_address'),
                'company_address': post.get('company_address'),
                'company_type': post.get('company_type'),
                'trade_license_number': post.get('trade_license_number'),
                'tax_identification_number': post.get('tax_identification_number'),
                'commencement_date': post.get('commencement_date'),
                'expiry_date': post.get('expiry_date'),
                'finance_contact_name': post.get('finance_contact_name'),
                'finance_contact_email': post.get('finance_contact_email'),
                'finance_contact_phone': post.get('finance_contact_phone'),
                'finance_contact_address': post.get('finance_contact_address'),
                'authorized_contact_name': post.get('authorized_contact_name'),
                'authorized_contact_email': post.get('authorized_contact_email'),
                'authorized_contact_phone': post.get('authorized_contact_phone'),
                'authorized_contact_address': post.get('authorized_contact_address'),
                'bank_name': post.get('bank_name'),
                'bank_address': post.get('bank_address'),
                'bank_swift_code': post.get('bank_swift_code'),
                'bank_account_name': post.get('bank_account_name'),
                'bank_account_number': post.get('bank_account_number'),
                'iban': post.get('iban'),

                #client information
                'client_1_name': post.get('client_1_name'),
                'client_1_email': post.get('client_1_email'),
                'client_1_phone': post.get('client_1_phone'),
                'client_1_address': post.get('client_1_address'),
                'client_2_name': post.get('client_2_name'),
                'client_2_email': post.get('client_2_email'),
                'client_2_phone': post.get('client_2_phone'),
                'client_2_address': post.get('client_2_address'),
                'client_3_name': post.get('client_3_name'),
                'client_3_email': post.get('client_3_email'),
                'client_3_phone': post.get('client_3_phone'),
                'client_3_address': post.get('client_3_address'),
                'client_4_name': post.get('client_4_name'),
                'client_4_email': post.get('client_4_email'),
                'client_4_phone': post.get('client_4_phone'),
                'client_4_address': post.get('client_4_address'),
                'client_5_name': post.get('client_5_name'),
                'client_5_email': post.get('client_5_email'),
                'client_5_phone': post.get('client_5_phone'),
                'client_5_address': post.get('client_5_address'),

                'certificate_name': post.get('certificate_name'),
                'certificate_number': post.get('certificate_number'),
                'certifying_body': post.get('certifying_body'),
                'award_date': post.get('award_date'),
                'cert_expiry_date': post.get('cert_expiry_date'),
                'signatory_name': post.get('signatory_name'),
                'authorized_signatory': post.get('authorized_signatory'),
                'declaration_confirm': True if post.get('declaration_confirm') == 'on' else False,
                'state': 'submitted'
            }
            
            # Process the company logo if uploaded
            if company_logo:
                try:
                    file_data = company_logo.read()
                    if file_data:
                        # Encode the image data properly
                        vals['company_logo'] = base64.b64encode(file_data).decode('utf-8')
                except Exception as e:
                    error_list.append(f"Error processing company logo: {str(e)}")
            
            # Process all documents
            for field, file in files.items():
                if file:
                    try:
                        file_data = file.read()
                        if file_data:
                            vals[field] = base64.b64encode(file_data).decode('utf-8')
                    except Exception as e:
                        error_list.append(f"Error processing file {field}: {str(e)}")
            
            # Create supplier application
            application = request.env['supplier.application'].sudo().create(vals)
            
            try:
                # Get all users in the reviewer group
                reviewer_group = request.env.ref('supplier_ms.group_reviewer')
                reviewers = reviewer_group.users

                if not reviewers:
                    _logger.warning("No reviewers found to notify about new supplier application")
                    return request.render("supplier_ms.portal_registration_success")

                # Send notification to each reviewer using the new mail function
                for reviewer in reviewers:
                    send_supplier_registration_reviewer_notification(
                        request.env,
                        application,
                        reviewer
                    )
                _logger.info(f"Supplier registration notification sent to reviewers: {reviewers.mapped('email')}")

            except Exception as e:
                _logger.error(f"Failed to send reviewer notification: {str(e)}")

            return request.render("supplier_ms.portal_registration_success")
        except Exception as e:
            error_list.append("An error occurred while submitting your application. Please try again.")
            return request.render("supplier_ms.portal_supplier_register_form", {
                'email': post.get('email'),
                'error_list': error_list,
                'form_data': post
            })



    @http.route('/supplier/register/success', type='http', auth="public", website=True)
    def supplier_register_success(self, **kwargs):
        return request.render("supplier_ms.portal_registration_success")
