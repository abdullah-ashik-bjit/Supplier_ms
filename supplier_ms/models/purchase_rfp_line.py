from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class RFPProductLine(models.Model):
    _name = 'purchase.rfp.product.line'
    _description = 'RFP Product Line'
    _rec_name = 'product_id'

    rfp_id = fields.Many2one(
        'purchase.rfp',
        string='RFP',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    description = fields.Text(string='Description')
    quantity = fields.Float(
        string='Quantity',
        required=True,
        default=1.0,
        digits='Product Unit of Measure'
    )
    unit_price = fields.Monetary(
        string='Unit Price',
        currency_field='currency_id',
        required=True,
        digits='Product Price',
        default=0.0,
        store=True
    )
    delivery_charges = fields.Monetary(
        string='Delivery Charges',
        currency_field='currency_id',
        digits='Product Price',
        default=0.0,
        store=True
    )
    subtotal_price = fields.Monetary(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True,
        currency_field='currency_id',
        digits='Product Price'
    )
    currency_id = fields.Many2one(
        related='rfp_id.currency_id',
        store=True,
        readonly=True
    )

    @api.depends('quantity', 'unit_price', 'delivery_charges')
    def _compute_subtotal(self):
        """Compute the subtotal including delivery charges"""
        for line in self:
            line.subtotal_price = (line.quantity * line.unit_price) + (line.delivery_charges or 0.0)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.display_name
            # Set default unit price from product's list price
            self.unit_price = self.product_id.list_price or 0.0
            # Reset delivery charges when product changes
            self.delivery_charges = 0.0

    @api.constrains('quantity', 'unit_price', 'delivery_charges')
    def _check_values(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_("Quantity must be greater than zero."))
            if line.unit_price < 0:
                raise ValidationError(_("Unit price cannot be negative."))
            if line.delivery_charges < 0:
                raise ValidationError(_("Delivery charges cannot be negative."))

class RFQLine(models.Model):
    _name = 'purchase.rfp.quotation.line'
    _description = 'RFQ Line'
    _rec_name = 'supplier_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    rfp_id = fields.Many2one(
        'purchase.rfp',
        string='RFP',
        required=True,
        ondelete='cascade'
    )
    supplier_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        required=True,
        domain=[('supplier_rank', '>', 0)]
    )
    expected_delivery_date = fields.Date(
        string='Expected Delivery Date',
        required=True,
        tracking=True
    )
    terms_conditions = fields.Html(
        string='Terms and Conditions',
        tracking=True
    )
    warranty_period = fields.Integer(
        string='Warranty Period (Months)',
        tracking=True
    )
    score = fields.Integer(
        string='Score',
        tracking=True
    )
    is_recommended = fields.Boolean(
        string='Recommended',
        tracking=True
    )
    product_line_ids = fields.One2many(
        'purchase.rfp.quotation.product.line',
        'rfq_id',
        string='Product Lines'
    )
    total_price = fields.Monetary(
        string='Total Price',
        compute='_compute_total_price',
        store=True,
        currency_field='currency_id',
        tracking=True
    )
    currency_id = fields.Many2one(
        related='rfp_id.currency_id'
    )

    @api.constrains('is_recommended')
    def _check_recommended(self):
        """Ensure only one RFQ can be recommended per RFP"""
        for rfq in self:
            if rfq.is_recommended:
                other_recommended = self.search([
                    ('rfp_id', '=', rfq.rfp_id.id),
                    ('is_recommended', '=', True),
                    ('id', '!=', rfq.id)
                ])
                if other_recommended:
                    raise ValidationError(_("Only one RFQ can be recommended per RFP."))

    @api.depends('product_line_ids.subtotal', 'product_line_ids.delivery_charges')
    def _compute_total_price(self):
        for rfq in self:
            product_total = sum(line.subtotal for line in rfq.product_line_ids)
            delivery_total = sum(line.delivery_charges or 0.0 for line in rfq.product_line_ids)
            rfq.total_price = product_total + delivery_total
            # Trigger recomputation of RFP total amount
            rfq.rfp_id._compute_total_amount()

    @api.onchange('expected_delivery_date')
    def _onchange_expected_delivery_date(self):
        """Validate delivery date is not in the past"""
        if self.expected_delivery_date and self.expected_delivery_date < fields.Date.today():
            raise ValidationError(_("Expected delivery date cannot be in the past."))

    @api.depends('expected_delivery_date', 'warranty_period', 'total_price', 'terms_conditions')
    def _compute_score(self):
        """Compute score based on delivery date, warranty, price, and terms"""
        for rfq in self:
            score = 0
            # Delivery date score (earlier is better)
            if rfq.expected_delivery_date:
                days_diff = (rfq.expected_delivery_date - fields.Date.today()).days
                score += max(0, 30 - days_diff)  # Max 30 points for delivery

            # Warranty period score
            score += min(rfq.warranty_period * 2, 30)  # Max 30 points for warranty

            # Price score (lower is better)
            if rfq.rfp_id.rfq_line_ids:
                avg_price = sum(rfq.rfp_id.rfq_line_ids.mapped('total_price')) / len(rfq.rfp_id.rfq_line_ids)
                if rfq.total_price < avg_price:
                    score += 30  # Max 30 points for price

            # Terms score (presence of terms)
            if rfq.terms_conditions:
                score += 10  # Max 10 points for terms

            rfq.score = score

    @api.model
    def create(self, vals):
        """Override create to compute score on creation"""
        res = super(RFQLine, self).create(vals)
        res._compute_score()  # Ensure score is computed on creation
        return res

class RFQProductLine(models.Model):
    _name = 'purchase.rfp.quotation.product.line'
    _description = 'RFQ Product Line'
    _rec_name = 'product_id'

    rfq_id = fields.Many2one(
        'purchase.rfp.quotation.line',
        string='RFQ',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    description = fields.Text(string='Description')
    quantity = fields.Integer(
        string='Quantity',
        required=True
    )
    unit_price = fields.Monetary(
        string='Unit Price',
        currency_field='currency_id',
        required=True
    )
    delivery_charges = fields.Monetary(
        string='Delivery Charges',
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        related='rfq_id.currency_id'
    )
    subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True,
        currency_field='currency_id'
    )

    @api.depends('quantity', 'unit_price', 'delivery_charges')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal_price = (line.quantity * line.unit_price) + (line.delivery_charges or 0.0)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.display_name