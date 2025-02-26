from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
import logging

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    rfp_id = fields.Many2one('purchase.rfp', string='RFP Reference')
    is_recommended = fields.Boolean(string='Recommended')
    warranty_period = fields.Integer(string='Warranty Period (Months)')
    rfp_state = fields.Selection(related='rfp_id.state', string='RFP Status', store=True)
    score = fields.Integer(string='Score', default=0)
    can_edit_score = fields.Boolean(compute='_compute_can_edit_score')
    terms_conditions = fields.Html(string='Terms and Conditions')
    expected_delivery_date = fields.Date(string='Expected Delivery Date')
    delivery_charges = fields.Monetary(
        string='Delivery Charges',
        currency_field='currency_id',
        default=0.0
    )

    @api.onchange('rfp_id')
    def _onchange_rfp_id(self):
        if self.rfp_id:
            self.origin = self.rfp_id.name
            self.currency_id = self.rfp_id.currency_id.id
            
            # Clear existing order lines
            self.order_line = [(5, 0, 0)]
            
            # Copy products from RFP without prices
            order_lines = []
            for line in self.rfp_id.product_line_ids:
                vals = {
                    'product_id': line.product_id.id,
                    'name': line.description or line.product_id.display_name,
                    'product_qty': line.quantity,
                    'product_uom': line.product_id.uom_po_id.id,
                    'date_planned': self.rfp_id.required_date,
                    'price_unit': 0.0,
                    'delivery_charges': 0.0,
                    'order_id': self.id,
                }
                order_lines.append((0, 0, vals))
            
            self.order_line = order_lines

    @api.constrains('rfp_id', 'partner_id')
    def _check_duplicate_quotation(self):
        pass


    def button_confirm(self):
        # Skip product validation for RFP-related purchase orders
        self = self.with_context(skip_rfp_product_check=True)
        res = super().button_confirm()
        for po in self:
            if po.rfp_id and po.rfp_id.state == 'approved':
                po.rfp_id.write({
                    'state': 'recommendation',
                    'selected_po_id': po.id
                })
        return res

    @api.depends('order_line.price_total', 'order_line.delivery_charges')
    def _amount_all(self):
        """Override to include delivery charges in total"""
        for order in self:
            amount_untaxed = amount_tax = total_delivery = 0.0
            
            for line in order.order_line:
                # Calculate base amount without delivery charges
                amount_untaxed += line.price_subtotal # Subtract delivery charges from subtotal
                amount_tax += line.price_tax
                total_delivery += line.delivery_charges

            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'delivery_charges': order.currency_id.round(total_delivery),
                'amount_total': order.currency_id.round(amount_untaxed + amount_tax + total_delivery),
            })

    @api.constrains('delivery_charges')
    def _check_delivery_charges(self):
        """Ensure delivery charges are not negative"""
        for order in self:
            if order.delivery_charges < 0:
                raise ValidationError(_("Delivery charges cannot be negative."))

    @api.constrains('rfp_id', 'expected_delivery_date', 'warranty_period')
    def _check_rfp_quotation(self):
        for po in self:
            if po.rfp_id:
                # Check delivery date is within RFP required date
                if po.expected_delivery_date > po.rfp_id.required_date:
                    raise ValidationError(_("Expected delivery date cannot be later than RFP required date."))
                
                # Check warranty period is reasonable
                if po.warranty_period < 0 or po.warranty_period > 60:  # Max 5 years
                    raise ValidationError(_("Warranty period must be between 0 and 60 months.")) 

    @api.constrains('rfp_id', 'order_line')
    def _check_rfp_products(self):
        # Skip validation if context flag is set
        if self.env.context.get('skip_rfp_product_check'):
            return
            
        for po in self:
            if po.rfp_id:
                # Get products with their names for better debugging
                rfp_products = set(po.rfp_id.product_line_ids.mapped('product_id.id'))
                po_products = set(po.order_line.mapped('product_id.id'))

                
                # Skip empty order lines (draft state)
                if not po_products and po.state == 'draft':
                    return
                
                # Check if products match exactly
                if rfp_products == po_products:
                    # Products match, now check quantities
                    for rfp_line in po.rfp_id.product_line_ids:
                        po_line = po.order_line.filtered(lambda l: l.product_id.id == rfp_line.product_id.id)
                        if po_line and po_line[0].product_qty != rfp_line.quantity:
                            raise ValidationError(_(
                                "Quantity mismatch for product '%s': RFP requires %s but quotation has %s"
                            ) % (rfp_line.product_id.display_name, rfp_line.quantity, po_line[0].product_qty))
                    return True  # All checks passed

                # If we get here, products don't match exactly
                missing_products = rfp_products - po_products
                extra_products = po_products - rfp_products

                error_message = []
                if missing_products:
                    missing_names = po.rfp_id.product_line_ids.filtered(
                        lambda l: l.product_id.id in missing_products
                    ).mapped('product_id.display_name')
                    error_message.append("Missing products: %s" % ', '.join(missing_names))

                if extra_products:
                    extra_names = po.order_line.filtered(
                        lambda l: l.product_id.id in extra_products
                    ).mapped('product_id.display_name')
                    error_message.append("Extra products: %s" % ', '.join(extra_names))

                if error_message:
                    raise ValidationError(_("Product mismatch between RFP and Quotation:\n%s") % '\n'.join(error_message))

    @api.depends_context('uid')
    def _compute_can_edit_score(self):
        """Compute if current user can edit score"""
        is_reviewer = self.env.user.has_group('supplier_ms.group_reviewer')
        for record in self:
            record.can_edit_score = is_reviewer

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    delivery_charges = fields.Monetary(
        string='Delivery Charges',
        currency_field='currency_id',
        default=0.0,
        copy=False  # Don't copy delivery charges when duplicating
    )

    @api.onchange('product_id')
    def onchange_product_id(self):
        """Override to prevent setting default price if from RFP"""
        if not self.product_id:
            return

        # Check if this is an RFP-related purchase order
        if self.order_id.rfp_id:
            self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
            self.product_qty = 1.0
            self.name = self.product_id.display_name
            self.price_unit = 0.0  # Always set price to 0 for RFP quotations
            self.date_planned = self.order_id.date_planned or fields.Datetime.now()
            return

        # If not from RFP, call the standard behavior
        result = super(PurchaseOrderLine, self).onchange_product_id()
        return result

    @api.depends('product_qty', 'price_unit', 'taxes_id', 'delivery_charges')
    def _compute_amount(self):
        """Override to include delivery charges in calculations"""
        for line in self:
            taxes = line.taxes_id.compute_all(
                line.price_unit,
                line.order_id.currency_id,
                line.product_qty,
                product=line.product_id,
                partner=line.order_id.partner_id
            )
            
            # Base amount is product cost * quantity
            base_amount = taxes['total_excluded']
            
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'] + line.delivery_charges,
                'price_subtotal': base_amount,
            })

    @api.onchange('delivery_charges')
    def _onchange_delivery_charges(self):
        """Trigger recomputation of order total when delivery charges change"""
        if self.delivery_charges:
            self.order_id._compute_amount_all()