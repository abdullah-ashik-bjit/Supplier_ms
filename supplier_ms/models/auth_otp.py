from odoo import models, fields, api
import random
from datetime import datetime, timedelta

class SupplierOTP(models.Model):
    _name = "supplier.otp"
    _description = "OTP for Supplier Email Verification"

    email = fields.Char(required=True)
    otp = fields.Char(required=True)
    expiration_time = fields.Datetime(required=True)

    @api.model
    def generate_otp(self, email):
        """Generate OTP and store it for verification"""
        otp_code = str(random.randint(100000, 999999))
        expiration = datetime.now() + timedelta(minutes=10)

        existing_otp = self.search([('email', '=', email)])
        if existing_otp:
            existing_otp.write({'otp': otp_code, 'expiration_time': expiration})
        else:
            self.create({'email': email, 'otp': otp_code, 'expiration_time': expiration})

        # # Send OTP via Email
        # template = self.env.ref('supplier_ms.email_template_supplier_otp')
        # if template:
        #     template.sudo().send_mail(self.id, force_send=True)

        mail_values={
        # 'email_from': 'abdullah74332@gmail.com',
        #set email_form to the current user's email
        'email_from': 'abdullah74332@gmail.com',
        'email_to': email,
        'subject': 'OTP for Supplier Registration',
        'body_html': f'Your OTP is: <b>{otp_code}</b>',
        }
        mail = self.env['mail.mail'].create(mail_values)
        mail.sudo().send()

        return otp_code

    def validate_otp(self, email, otp):
        """Validate OTP for email verification"""
        otp_record = self.search([('email', '=', email), ('otp', '=', otp)], limit=1)
        if otp_record and otp_record.expiration_time > datetime.now():
            otp_record.unlink()  # Remove OTP after successful verification
            return True
        return False
