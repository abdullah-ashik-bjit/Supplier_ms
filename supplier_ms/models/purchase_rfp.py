from odoo import models, fields, api, _
from datetime import timedelta
from odoo.exceptions import UserError, ValidationError
import logging
from odoo.osv import expression
from ..data.mail_utils import (
    send_rfp_submitted_notification,
    send_rfp_approved_notification,
    send_rfp_rejected_notification,
    send_rfp_to_suppliers_notification,
    send_rfp_supplier_selected_notification,
    send_rfp_accepted_notification,
    send_quotation_rejection_notification,
    send_rfp_closure_notification,
    send_rfp_recommendation_notification
)
_logger = logging.getLogger(__name__)



class RFPStateHistory(models.Model):
    _name = 'purchase.rfp.state.history'
    _description = 'RFP State History'
    _order = 'create_date desc'

    rfp_id = fields.Many2one('purchase.rfp', string='RFP', required=True, ondelete='cascade')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('closed', 'Closed'),
        ('recommendation', 'Recommendation'),
        ('accepted', 'Accepted')
    ], string='State', required=True)
    create_date = fields.Datetime(string='Date', readonly=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True, default=lambda self: self.env.user)


class PurchaseRFP(models.Model):
    _name = 'purchase.rfp'
    _description = 'Request for Purchase'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    # _mail_post_access = 'read'
    _order = 'create_date desc'

    name = fields.Char(
        string='RFP Number',
        readonly=True,
        default='New',
        tracking=True
    )
    
    rfp_id = fields.Char(
        string='RFP ID', 
        readonly=True, 
        copy=False,
        tracking=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('closed', 'Closed'),
        ('recommendation', 'Recommended'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')
    ], default='draft', tracking=True, string='Status')

    required_date = fields.Date(
        string='Required Date',
        default=lambda self: fields.Date.today() + timedelta(days=7),
        tracking=True
    )
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_total_amount',
        store=True,
        currency_field='currency_id',
        tracking=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id.id,
        tracking=True
    )
    approved_supplier_id = fields.Many2one(
        'res.partner',
        string='Approved Supplier',
        domain="[('supplier_rank', '>', 0)]",
        tracking=True,
       readonly={'recommendation': [('readonly', False)]},
        groups="supplier_ms.group_approver,supplier_ms.group_reviewer"
    )

    # Product Lines
    product_line_ids = fields.One2many(
        'purchase.rfp.product.line',
        'rfp_id',
        string='Product Lines'
    )

    # Replace custom RFQ lines with purchase orders
    purchase_order_ids = fields.One2many(
        'purchase.order',
        'rfp_id',
        string='Quotations',
        domain=[('state', 'in', ['draft', 'sent', 'purchase'])]
    )
    selected_po_id = fields.Many2one(
        'purchase.order',
        string='Selected Purchase Order',
        readonly=True
    )

    # Comments
    reviewer_comments = fields.Text(string='Reviewer Comments', tracking=True)
    approver_comments = fields.Text(
        string='Approver Comments', 
        tracking=True
    )

    # Add these fields
    quotation_count = fields.Integer(
        string='Quotation Count',
        compute='_compute_quotation_count',
        store=True
    )

    # Add this computed field for counting
    rfp_count = fields.Integer(string='Count', compute='_compute_rfp_count', store=True)

    # # Add missing log access fields explicitly
    # create_uid = fields.Many2one('res.users', string='Created by', readonly=True)
    # create_date = fields.Datetime(string='Created on', readonly=True)
    # write_uid = fields.Many2one('res.users', string='Last Updated by', readonly=True)
    # write_date = fields.Datetime(string='Last Updated on', readonly=True)

    # Add state history field
    state_history = fields.One2many('purchase.rfp.state.history', 'rfp_id', string='State History')

    # Add user_id field
    user_id = fields.Many2one(
        'res.users', 
        string='Created By',
        default=lambda self: self.env.user,
        tracking=True,
        readonly=True
    )

    # Add approver_id field
    approver_id = fields.Many2one(
        'res.users',
        string='Approver',
        domain="[('groups_id', 'in', [(6, 0, [self.env.ref('supplier_ms.group_approver').id])])]",
        tracking=True
    )

    def can_access_from_portal(self):
        """Check if current user can access this RFP from portal"""
        self.ensure_one()
        return (
            self.state == 'approved' or 
            self.purchase_order_ids.filtered(
                lambda po: po.partner_id.id == self.env.user.partner_id.id
            )
        )

    @api.model
    def create(self, vals):
        # # Check if user is in reviewer group
        # if not self.env.user.has_group('supplier_ms.group_reviewer'):
        #     raise ValidationError(_("Only reviewers can create RFPs."))
        
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.rfp') or 'New'
        return super(PurchaseRFP, self).create(vals)

    @api.depends('selected_po_id.amount_total', 'selected_po_id', 'state')
    def _compute_total_amount(self):
        """Compute total amount from the accepted purchase order"""
        for rfp in self:
            if rfp.state == 'accepted' and rfp.selected_po_id:
                rfp.total_amount = rfp.selected_po_id.amount_total
            else:
                rfp.total_amount = 0.0

    @api.depends('purchase_order_ids')
    def _compute_quotation_count(self):
        for rfp in self:
            rfp.quotation_count = len(rfp.purchase_order_ids)

    @api.depends()
    def _compute_rfp_count(self):
        for record in self:
            record.rfp_count = 1  # Each record counts as 1

    def action_submit(self):
        """Submit RFP for approval"""
        self.ensure_one()
        if not self.env.user.has_group('supplier_ms.group_reviewer'):
            raise ValidationError(_("Only reviewers can submit RFPs."))
            
        if self.state != 'draft':
            raise ValidationError(_("Only draft RFPs can be submitted."))
            
        if not self.product_line_ids:
            raise ValidationError(_("Cannot submit RFP without product lines."))

        try:
            self.write({'state': 'submitted'})
            
            approver_group = self.env.ref('supplier_ms.group_approver')
            approvers = approver_group.users

            if not approvers:
                raise ValidationError(_("No approvers found in the system."))

            for approver in approvers:
                send_rfp_submitted_notification(
                    self.env, 
                    self, 
                    approver.email, 
                    approver.name
                )

            # return {
            #     'type': 'ir.actions.client',
            #     'tag': 'display_notification',
            #     'params': {
            #         'title': _('Success'),
            #         'message': _('RFP submitted successfully'),
            #         'type': 'success',
            #         'sticky': False,
            #     }
            # }

        except Exception as e:
            _logger.error(f"Failed to submit RFP: {str(e)}")
            raise UserError(_("Failed to submit RFP: %s") % str(e))

    def action_approve(self):
        """Approve RFP"""
        self.ensure_one()
        if not self.env.user.has_group('supplier_ms.group_approver'):
            raise ValidationError(_("Only approvers can approve RFPs."))
            
        if self.state != 'submitted':
            raise ValidationError(_("Only submitted RFPs can be approved."))
            
        if not self.product_line_ids:
            raise ValidationError(_("Cannot approve RFP without product lines."))
        
        self.write({
            'state': 'approved',
            'approved_supplier_id': False,
            'approver_id': self.env.user.id
        })
        

        try:
            self.write({'state': 'approved'})
            
            # Send approval notification
            send_rfp_approved_notification(self.env, self)
            
            # Send to selected suppliers
            for supplier in self.supplier_ids:
                send_rfp_to_suppliers_notification(self.env, self, supplier)

            # return {
            #     'type': 'ir.actions.client',
            #     'tag': 'display_notification',
            #     'params': {
            #         'title': _('Success'),
            #         'message': _('RFP approved and sent to suppliers'),
            #         'type': 'success',
            #         'sticky': False,
            #     }
            # }

        except Exception as e:
            _logger.error(f"Failed to approve RFP: {str(e)}")
            raise UserError(_("Failed to approve RFP: %s") % str(e))

    def action_reject(self):
        """Reject RFP"""
        self.ensure_one()
        if not self.env.user.has_group('supplier_ms.group_approver'):
            raise ValidationError(_("Only approvers can reject RFPs."))
            
        if self.state != 'submitted':
            raise ValidationError(_("Only submitted RFPs can be rejected."))
            
        if not self.approver_comments:
            raise ValidationError(_("Please provide rejection reason in approver comments."))

        try:
            self.write({
                'state': 'rejected',
                'approver_id': self.env.user.id
            })
            send_rfp_rejected_notification(self.env, self, self.approver_comments)

            # return {
            #     'type': 'ir.actions.client',
            #     'tag': 'display_notification',
            #     'params': {
            #         'title': _('Success'),
            #         'message': _('RFP rejected'),
            #         'type': 'success',
            #         'sticky': False,
            #     }
            # }

        except Exception as e:
            _logger.error(f"Failed to reject RFP: {str(e)}")
            raise UserError(_("Failed to reject RFP: %s") % str(e))

    def action_select_supplier(self):
        """Select supplier and create PO"""
        self.ensure_one()
        if not self.env.user.has_group('supplier_ms.group_approver'):
            raise ValidationError(_("Only approvers can select suppliers."))
            
        if self.state != 'approved':
            raise ValidationError(_("Can only select supplier for approved RFPs."))
            
        if not self.approved_supplier_id:
            raise ValidationError(_("Please select a supplier first."))

        try:
            # Create PO
            po = self._create_purchase_order()
            
            # Update RFP
            self.write({
                'state': 'done',
                'selected_po_id': po.id
            })
            
            # Send notifications
            send_rfp_supplier_selected_notification(self.env, self, po)
            
            # Send rejection notifications to other suppliers
            for quotation in self.quotation_ids.filtered(
                lambda q: q.partner_id != self.approved_supplier_id
            ):
                send_quotation_rejection_notification(
                    self.env, 
                    self, 
                    quotation.partner_id.email
                )

            # return {
            #     'type': 'ir.actions.client',
            #     'tag': 'display_notification',
            #     'params': {
            #         'title': _('Success'),
            #         'message': _('Supplier selected and PO created'),
            #         'type': 'success',
            #         'sticky': False,
            #     }
            # }

        except Exception as e:
            _logger.error(f"Failed to select supplier: {str(e)}")
            raise UserError(_("Failed to select supplier: %s") % str(e))

    def action_close(self):
        """Close RFP for quotations"""
        self.ensure_one()
        
        if not self.env.user.has_group('supplier_ms.group_approver'):
            raise ValidationError(_("Only approvers can close RFPs."))
            
        if self.state != 'approved':
            raise ValidationError(_("Only approved RFPs can be closed."))
            
        if not self.purchase_order_ids:
            raise ValidationError(_("Cannot close RFP without any quotations."))
            
        try:
            self.write({'state': 'closed'})
            
            # Notify suppliers using new mail function
            for supplier in self.purchase_order_ids.mapped('partner_id'):
                send_rfp_closure_notification(self.env, self, supplier.email)

            # return {
            #     'type': 'ir.actions.client',
            #     'tag': 'display_notification',
            #     'params': {
            #         'title': _('Success'),
            #         'message': _('RFP closed successfully'),
            #         'type': 'success',
            #         'sticky': False,
            #     }
            # }
        except Exception as e:
            _logger.error(f"Failed to close RFP: {str(e)}")
            raise UserError(_("Failed to close RFP: %s") % str(e))

    def action_recommend(self):
        """Move to recommendation state where approver can select the winning supplier"""
        self.ensure_one()
        
        if not self.env.user.has_group('supplier_ms.group_reviewer'):
            raise ValidationError(_("Only reviewers can recommend RFPs."))
            
        if self.state != 'closed':
            raise ValidationError(_("Only closed RFPs can be moved to recommendation."))
            
        if not self.purchase_order_ids:
            raise ValidationError(_("Cannot recommend without any quotations submitted."))
            
        try:
            self.write({'state': 'recommendation'})
            
            # Send recommendation notification using new mail function
            send_rfp_recommendation_notification(self.env, self)

            # return {
            #     'type': 'ir.actions.client',
            #     'tag': 'display_notification',
            #     'params': {
            #         'title': _('Success'),
            #         'message': _('RFP moved to recommendation stage'),
            #         'type': 'success',
            #         'sticky': False,
            #     }
            # }
        except Exception as e:
            _logger.error(f"Failed to move RFP to recommendation: {str(e)}")
            raise UserError(_("Failed to process recommendation: %s") % str(e))

    def action_accept(self):
        """Accept the RFP and selected supplier"""
        self.ensure_one()
        
        if not self.env.user.has_group('supplier_ms.group_approver'):
            raise ValidationError(_("Only approvers can accept RFPs."))
            
        if self.state != 'recommendation':
            raise ValidationError(_("Only RFPs in recommendation stage can be accepted."))
            
        if not self.approved_supplier_id:
            raise ValidationError(_("Cannot accept RFP without selecting a supplier."))

        # Check if supplier has submitted a quotation and also that is a recommended quotation
        supplier_quotation = self.purchase_order_ids.filtered(
            lambda po: po.partner_id.id == self.approved_supplier_id.id and po.is_recommended
        )

        if not supplier_quotation:
            raise ValidationError(_("Selected supplier has not submitted a quotation."))

        # Get the winning quotation
        winning_quotation = supplier_quotation[0]

        try:
            # Update RFP state and link winning quotation
            self.write({
                'state': 'accepted',
                'selected_po_id': winning_quotation.id,
                'total_amount': winning_quotation.amount_total,
                'acceptance_date': fields.Datetime.now(),
                'accepted_by': self.env.user.id
            })

            # Confirm the winning quotation
            winning_quotation.button_confirm()
            
            # Send acceptance notification using new mail function
            send_rfp_accepted_notification(self.env, self)
            
            return True
            
        except Exception as e:
            _logger.error(f"Failed to accept RFP: {str(e)}")
            raise UserError(_("Failed to accept RFP: %s") % str(e))

    def action_return_draft(self):
        """Return RFP to draft state"""
        self.ensure_one()
        
        if not self.env.user.has_group('supplier_ms.group_reviewer'):
            raise ValidationError(_("Only reviewers can return RFPs to draft."))
            
        if self.state != 'submitted':
            raise ValidationError(_("Only submitted RFPs can be returned to draft."))
            
        self.write({'state': 'draft'})
        return True

    def action_view_quotations(self):
        self.ensure_one()
        return {
            'name': _('Quotations'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'domain': [('rfp_id', '=', self.id)],
            'context': {
                'default_rfp_id': self.id,
                'default_origin': self.name,
                'default_date_planned': self.required_date,
            }
        }

    def recompute_totals(self):
        """Force recomputation of totals"""
        self.ensure_one()
        self.product_line_ids._compute_subtotal()
        self._compute_total_amount()
        return True

    @api.constrains('state', 'product_line_ids', 'purchase_order_ids')
    def _check_state_transitions(self):
        for rfp in self:
            if rfp.state == 'approved' and not rfp.product_line_ids:
                raise ValidationError(_("Cannot approve RFP without product lines."))
            
            if rfp.state == 'closed' and not rfp.purchase_order_ids:
                raise ValidationError(_("Cannot close RFP without any quotations."))
            
            if rfp.state == 'recommendation':
                recommended = rfp.purchase_order_ids.filtered('is_recommended')
                if not recommended:
                    raise ValidationError(_("Cannot move to recommendation state without recommending a quotation."))

    @api.constrains('required_date')
    def _check_required_date(self):
        for rfp in self:
            if rfp.required_date and rfp.required_date < fields.Date.today():
                raise ValidationError(_("Required date cannot be in the past."))

    @api.constrains('product_line_ids')
    def _check_product_lines(self):
        for rfp in self:
            if rfp.state != 'draft' and not rfp.product_line_ids:
                raise ValidationError(_("RFP must have at least one product line."))
            for line in rfp.product_line_ids:
                if line.quantity <= 0:
                    raise ValidationError(_("Product quantity must be greater than zero."))

    @api.constrains('purchase_order_ids')
    def _check_recommendations(self):
        """
        Ensure only one quotation per supplier can be recommended for an RFP.
        Multiple suppliers can have recommended quotations.
        """
        for rfp in self:
            recommended_quotations = rfp.purchase_order_ids.filtered(lambda q: q.is_recommended)
            for quote in recommended_quotations:
                if quote.score < 50:
                    raise ValidationError(_("Quotation score should be greater than 50"))
            # Group recommended quotations by supplier
            supplier_quotations = {}
            for quote in recommended_quotations:
                if quote.partner_id in supplier_quotations:
                    raise ValidationError(_(
                        'Multiple quotations from the same supplier (%s) cannot be recommended for RFP %s. '
                        'Please ensure only one quotation per supplier is recommended.',
                        quote.partner_id.name, rfp.name
                    ))
                supplier_quotations[quote.partner_id] = quote

    @api.constrains('state')
    def _check_state_sequence(self):
        for rfp in self:
            if rfp.state == 'approved' and not rfp.state_history.filtered(lambda h: h.state == 'submitted'):
                raise ValidationError(_("RFP must be submitted before approval."))
            if rfp.state == 'recommendation' and not rfp.state_history.filtered(lambda h: h.state == 'closed'):
                raise ValidationError(_("RFP must be closed before recommendation."))
            if rfp.state == 'accepted' and not rfp.state_history.filtered(lambda h: h.state == 'recommendation'):
                raise ValidationError(_("RFP must be in recommendation state before acceptance."))

    @api.constrains('state', 'approved_supplier_id')
    def _check_approved_supplier(self):
        """Ensure approved supplier is selected for certain states"""
        for record in self:
            if record.state == 'accepted' and not record.approved_supplier_id:
                raise ValidationError(_("An approved supplier must be selected for accepting the RFP."))

    @api.constrains('state', 'purchase_order_ids')
    def _check_recommendation_state(self):
        for record in self:
            if record.state == 'recommendation':
                recommended = record.purchase_order_ids.filtered(lambda po: po.is_recommended)
                if not recommended:
                    raise ValidationError(_("At least one quotation must be recommended before moving to recommendation state."))

    def write(self, vals):
        """Override write to track state changes"""
        if 'state' in vals:
            self.env['purchase.rfp.state.history'].create({
                'rfp_id': self.id,
                'state': vals['state'],
            })
        return super(PurchaseRFP, self).write(vals)
