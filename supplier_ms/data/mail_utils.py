from odoo import _
from odoo.exceptions import UserError
import logging
from odoo.fields import Datetime


def send_rfp_submitted_notification(env, rfp, recipient_email, recipient_name):
    """Send notification when RFP is submitted"""
    try:
        mail_values = {
            'email_from': env.user.company_id.email,
            'email_to': recipient_email,
            'subject': f'RFP {rfp.name} Submitted for Approval',
            'body_html': f"""
                <div style="margin: 0px; padding: 0px;">
                    <p>Dear {recipient_name},</p>
                    <p>The RFP {rfp.name} has been submitted for your approval.</p>
                    <p><a href="/web#id={rfp.id}&model=purchase.rfp&view_type=form">View RFP</a></p>
                    <p>Best regards,<br/>{env.user.company_id.name}</p>
                </div>
            """
        }
        env['mail.mail'].sudo().create(mail_values).send()
    except Exception as e:
        raise UserError(_("Failed to send notification email"))

def send_rfp_approved_notification(env, rfp):
    """Send notification when RFP is approved"""
    try:
        mail_values = {
            'email_from': env.user.company_id.email,
            'email_to': rfp.create_uid.email,
            'subject': f'RFP {rfp.name} Has Been Approved',
            'body_html': f"""
                <div style="margin: 0px; padding: 0px;">
                    <p>Dear {rfp.create_uid.name},</p>
                    <p>Your RFP {rfp.name} has been approved.</p>
                    <p>The RFP is now open for supplier quotations.</p>
                    <p><a href="/web#id={rfp.id}&model=purchase.rfp&view_type=form">View RFP</a></p>
                    <p>Best regards,<br/>{env.user.company_id.name}</p>
                </div>
            """
        }
        env['mail.mail'].sudo().create(mail_values).send()
    except Exception as e:
        raise UserError(_("Failed to send notification email"))

def send_rfp_rejected_notification(env, rfp, rejection_reason):
    """Send notification when RFP is rejected"""
    try:
        mail_values = {
            'email_from': env.user.company_id.email,
            'email_to': rfp.user_id.email,
            'subject': f'RFP {rfp.name} Has Been Rejected',
            'body_html': f"""
                <div>
                    <p>Dear {rfp.user_id.name},</p>
                    <p>Your RFP {rfp.name} has been rejected.</p>
                    <p><strong>Rejection Reason:</strong></p>
                    <p>{rejection_reason or 'No reason provided.'}</p>
                    <p>You can review the RFP in the system.</p>
                </div>
            """
        }
        env['mail.mail'].sudo().create(mail_values).send()
    except Exception as e:
        raise UserError(_("Failed to send notification email"))

def send_supplier_review_approval(env, application, approver):
    """Send notification when supplier application is reviewed and approved"""
    try:
        mail_values = {
            'email_from': env.user.company_id.email,
            'email_to': approver.email,
            'subject': f'Supplier Application {application.company_name} - Review Approved',
            'body_html': f"""
                <div style="margin: 0px; padding: 0px;">
                    <p>Dear {approver.name},</p>
                    <p>A supplier application has been reviewed and approved. Your final approval is required.</p>
                    <ul>
                        <li>Company: {application.company_name}</li>
                        <li>Email: {application.email}</li>
                        <li>Review Comments: {application.reviewer_comments or 'No comments'}</li>
                    </ul>
                    <p><a href="/web#id={application.id}&model=supplier.application&view_type=form">Review Application</a></p>
                    <p>Best regards,<br/>{env.user.company_id.name}</p>
                </div>
            """
        }
        env['mail.mail'].sudo().create(mail_values).send()
    except Exception as e:
        raise UserError(_("Failed to send notification email"))

def send_supplier_final_approval(env, application, password):
    """Send approval notification to supplier with credentials"""
    try:
        mail_values = {
            'email_from': env.user.company_id.email,
            'email_to': application.email,
            'subject': f'Supplier Application {application.company_name} Approved',
            'body_html': f"""
                <div style="margin: 0px; padding: 0px;">
                    <p>Dear {application.company_name},</p>
                    <p>Your supplier application has been approved.</p>
                    <p>Access credentials:</p>
                    <ul>
                        <li>Username: {application.email}</li>
                        <li>Password: {password}</li>
                    </ul>
                    <p><a href="/web/login">Access Portal</a></p>
                    <p>Please change your password after first login.</p>
                    <p>Best regards,<br/>{env.user.company_id.name}</p>
                </div>
            """
        }
        env['mail.mail'].sudo().create(mail_values).send()
    except Exception as e:
        raise UserError(_("Failed to send approval email"))

def send_supplier_blacklist_notification(env, application):
    """Send notification when supplier is blacklisted"""
    try:
        mail_values = {
            'email_from': env.user.company_id.email,
            'email_to': application.email,
            'subject': f'Supplier Application Status Update - {application.company_name}',
            'body_html': f"""
                <div style="margin: 0px; padding: 0px;">
                    <p>Dear {application.company_name},</p>
                    <p>We regret to inform you that your supplier application has been rejected 
                    and your email has been added to our blacklist.</p>
                    <p>Reason: {application.reviewer_comments or ''}</p>
                    <p>If you believe this is an error, please contact our support team.</p>
                    <br/>
                    <p>Best regards,<br/>{env.user.company_id.name}</p>
                </div>
            """
        }
        env['mail.mail'].sudo().create(mail_values).send()
    except Exception as e:
        raise UserError(_("Failed to send notification email"))

def send_supplier_registration_notification(env, application, reviewer):
    """Send notification to reviewer about new supplier registration"""
    try:
        mail_values = {
            'email_from': env.user.company_id.email,
            'email_to': reviewer.email,
            'subject': f'New Supplier Registration: {application.company_name}',
            'body_html': f"""
                <div style="margin: 0px; padding: 0px;">
                    <p>Dear {reviewer.name},</p>
                    <p>A new supplier registration application has been submitted for your review.</p>
                    
                    <div style="margin: 16px 0px;">
                        <strong>Company Details:</strong>
                        <ul>
                            <li>Company Name: {application.company_name}</li>
                            <li>Company Type: {application.company_type}</li>
                            <li>Email: {application.email}</li>
                            <li>Submission Date: {application.create_date}</li>
                        </ul>
                    </div>
                    
                    <p><a href="/web#id={application.id}&model=supplier.application&view_type=form">View Application</a></p>
                    <p>Best regards,<br/>{env.user.company_id.name}</p>
                </div>
            """
        }
        env['mail.mail'].sudo().create(mail_values).send()
    except Exception as e:
        raise UserError(_("Failed to send notification email"))

def send_final_approval_notification(env, application, approver):
    """Send notification for final approval stage"""
    try:
        mail_values = {
            'email_from': env.user.company_id.email,
            'email_to': approver.email,
            'subject': f'Supplier Application {application.company_name} - Final Approval Stage',
            'body_html': f"""
                <div style="margin: 0px; padding: 0px;">
                    <p>Dear {approver.name},</p>
                    <p>A supplier application has been reviewed and is ready for final approval.</p>
                    
                    <div style="margin: 16px 0px;">
                        <strong>Application Details:</strong>
                        <ul>
                            <li>Company: {application.company_name}</li>
                            <li>Email: {application.email}</li>
                            <li>Reviewer Comments: {application.reviewer_comments or 'No comments'}</li>
                        </ul>
                    </div>
                    
                    <p><a href="/web#id={application.id}&model=supplier.application&view_type=form">Review Application</a></p>
                    <p>Best regards,<br/>{env.user.company_id.name}</p>
                </div>
            """
        }
        env['mail.mail'].sudo().create(mail_values).send()
    except Exception as e:
        raise UserError(_("Failed to send notification email"))

def send_final_rejection_notification(env, application):
    """Send final rejection notification to supplier"""
    try:
        mail_values = {
            'email_from': env.user.company_id.email,
            'email_to': application.email,
            'subject': f'Supplier Application Status Update - {application.company_name}',
            'body_html': f"""
                <div style="margin: 0px; padding: 0px;">
                    <p>Dear {application.company_name},</p>
                    <p>After careful review, we regret to inform you that your supplier application has been rejected.</p>
                    
                    {f'<p>Reason: {application.approver_comments}</p>' if application.approver_comments else ''}
                    
                    <p>If you have any questions, please contact our support team.</p>
                    <br/>
                    <p>Best regards,<br/>{env.user.company_id.name}</p>
                </div>
            """
        }
        env['mail.mail'].sudo().create(mail_values).send()
    except Exception as e:
        raise UserError(_("Failed to send notification email"))

def send_rfp_closure_notification(env, rfp, supplier_email):
    """Send RFP closure notification to suppliers"""
    try:
        mail_values = {
            'email_from': env.user.company_id.email,
            'email_to': supplier_email,
            'subject': f'RFP {rfp.name} - Closed',
            'body_html': f"""
                <div style="margin: 0px; padding: 0px;">
                    <p>Dear Supplier,</p>
                    <p>The RFP {rfp.name} has been closed.</p>
                    <p>Thank you for your participation.</p>
                    <br/>
                    <p>Best regards,<br/>{env.user.company_id.name}</p>
                </div>
            """
        }
        env['mail.mail'].sudo().create(mail_values).send()
    except Exception as e:
        raise UserError(_("Failed to send notification email"))

def send_quotation_rejection_notification(env, rfp, supplier_email):
    """Send notification when quotation is rejected"""
    try:
        mail_values = {
            'email_from': env.user.company_id.email,
            'email_to': supplier_email,
            'subject': f'Quotation Status Update - RFP {rfp.name}',
            'body_html': f"""
                <div style="margin: 0px; padding: 0px;">
                    <p>Dear Supplier,</p>
                    <p>We regret to inform you that your quotation for RFP {rfp.name} has not been selected.</p>
                    <p>Thank you for your participation.</p>
                    <br/>
                    <p>Best regards,<br/>{env.user.company_id.name}</p>
                </div>
            """
        }
        env['mail.mail'].sudo().create(mail_values).send()
    except Exception as e:
        raise UserError(_("Failed to send notification email"))

def send_rfp_to_suppliers_notification(env, rfp, supplier):
    """Send RFP notification to suppliers"""
    try:
        mail_values = {
            'email_from': env.user.company_id.email,
            'email_to': supplier.email,
            'subject': f'New RFP Available: {rfp.name}',
            'body_html': f"""
                <div style="margin: 0px; padding: 0px;">
                    <p>Dear {supplier.name},</p>
                    <p>A new Request for Purchase ({rfp.name}) is available for quotation.</p>
                    <p>Required Date: {rfp.required_date}</p>
                    <p>You can submit your quotation through the supplier portal:</p>
                    <div style="margin: 16px 0px;">
                        <a href="/my/rfp/{rfp.id}" style="background-color: #875A7B; padding: 8px 16px; text-decoration: none; color: #fff; border-radius: 5px;">
                            Submit Quotation
                        </a>
                    </div>
                    <p>Best regards,<br/>{env.user.company_id.name}</p>
                </div>
            """
        }
        env['mail.mail'].sudo().create(mail_values).send()
    except Exception as e:
        raise UserError(_("Failed to send notification email"))

def send_rfp_recommendation_notification(env, rfp):
    """Send RFP recommendation notification"""
    try:
        mail_values = {
            'email_from': env.user.company_id.email,
            'email_to': rfp.create_uid.email,
            'subject': f'RFP {rfp.name} - Recommendation for Review',
            'body_html': f"""
                <div>
                    <p>Dear {rfp.create_uid.name},</p>
                    <p>RFP {rfp.name} has been reviewed and a supplier has been recommended for your approval.</p>
                    <p>Please review the recommendation at your earliest convenience.</p>
                    <br/>
                    <p>Best regards,</p>
                    <p>{env.user.name}</p>
                </div>
            """
        }
        env['mail.mail'].sudo().create(mail_values).send()
    except Exception as e:
        raise UserError(_("Failed to send notification email"))

def send_rfp_supplier_selected_notification(env, rfp, purchase_order):
    """Send notification to selected supplier"""
    try:
        mail_values = {
            'email_from': env.user.company_id.email,
            'email_to': rfp.approved_supplier_id.email,
            'subject': f'Your Quotation Selected for RFP {rfp.name}',
            'body_html': f"""
                <div>
                    <p>Dear {rfp.approved_supplier_id.name},</p>
                    <p>Your quotation has been selected for RFP {rfp.name}.</p>
                    <p>A purchase order {purchase_order.name} has been created and will be sent to you shortly.</p>
                    <br/>
                    <p>Best regards,</p>
                    <p>{rfp.user_id.name}</p>
                </div>
            """
        }
        env['mail.mail'].sudo().create(mail_values).send()
    except Exception as e:
        raise UserError(_("Failed to send notification email"))

def send_rfp_accepted_notification(env, rfp):
    """Send RFP acceptance notification"""
    try:
        mail_values = {
            'email_from': env.user.company_id.email,
            'email_to': rfp.create_uid.email,
            'subject': f'RFP {rfp.name} - Final Acceptance',
            'body_html': f"""
                <div>
                    <p>Dear {rfp.create_uid.name},</p>
                    <p>The RFP {rfp.name} has been finalized and accepted.</p>
                    <p>Selected Supplier: {rfp.approved_supplier_id.name}</p>
                    <p>Purchase Order: {rfp.selected_po_id.name}</p>
                    <br/>
                    <p>Best regards,</p>
                    <p>{env.user.name}</p>
                </div>
            """
        }
        env['mail.mail'].sudo().create(mail_values).send()
    except Exception as e:
        raise UserError(_("Failed to send notification email"))

def send_supplier_registration_reviewer_notification(env, application, reviewer):
    """Send notification to reviewer about new supplier registration from portal"""
    try:
        mail_values = {
            'email_from': env.user.company_id.email,
            'email_to': reviewer.email,
            'subject': f'New Supplier Registration: {application.company_name}',
            'body_html': f"""
                <div style="margin: 0px; padding: 0px;">
                    <p>Dear {reviewer.name},</p>
                    <p>A new supplier registration has been submitted through the portal for your review.</p>
                    
                    <div style="margin: 16px 0px;">
                        <strong>Company Details:</strong>
                        <ul>
                            <li>Company Name: {application.company_name}</li>
                            <li>Email: {application.email}</li>
                            <li>Submission Date: {Datetime.now()}</li>
                        </ul>
                    </div>
                    
                    <p><a href="/web#id={application.id}&model=supplier.application&view_type=form"
                          style="background-color: #875A7B; padding: 8px 16px; text-decoration: none; color: #fff; border-radius: 5px;">
                        Review Application
                    </a></p>
                    
                    <p>Best regards,<br/>{env.user.company_id.name}</p>
                </div>
            """
        }
        env['mail.mail'].sudo().create(mail_values).send()
    except Exception as e:
        raise UserError(_("Failed to send notification email"))

def send_rfq_submitted_notification(env, rfp, purchase_order):
    """
    Send notification when supplier submits a quotation for an RFP
    
    Args:
        env: Odoo environment
        rfp: purchase.rfp record
        purchase_order: purchase.order record
    """
    try:
        template = env.ref('supplier_ms.email_template_rfq_submitted', raise_if_not_found=False)
        if template:
            template.sudo().with_context(
                rfp_name=rfp.name,
                supplier_name=purchase_order.partner_id.name
            ).send_mail(
                purchase_order.id,
                force_send=True
            )
            _logger.info(
                f"RFQ submission notification sent for RFP: {rfp.name} from supplier: {purchase_order.partner_id.name}"
            )
    except Exception as e:
        _logger.error(f"Failed to send RFQ submission notification: {str(e)}")
