from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class SupplierDashboard(models.Model):
    _name = 'supplier.dashboard'
    _description = 'Supplier Dashboard Data'

    @api.model
    def get_supplier_metrics(self, supplier_id=False, date_range='this_week'):
        """Fetch supplier-specific RFQ data for the selected date range."""
        domain = [('state', 'in', ['purchase', 'done'])]

        if supplier_id:
            domain.append(('partner_id', '=', supplier_id))

        today = fields.Date.today()
        date_filters = {
            'this_week': today - timedelta(days=today.weekday()),
            'last_week': today - timedelta(days=today.weekday() + 7),
            'last_month': today.replace(day=1) - timedelta(days=1),
            'last_year': today.replace(month=1, day=1) - timedelta(days=365),
        }
        start_date = date_filters.get(date_range, today - timedelta(days=7))
        
        # Calculate previous period
        period_length = today - start_date
        previous_end = start_date
        previous_start = previous_end - period_length

        # Current period domain
        current_domain = domain + [
            ('date_order', '>=', start_date),
            ('date_order', '<=', today)
        ]

        # Previous period domain
        previous_domain = domain + [
            ('date_order', '>=', previous_start),
            ('date_order', '<', previous_end)
        ]

        # Get current period data
        current_rfqs = self.env['purchase.order'].search(current_domain)
        total_rfqs = len(current_rfqs)
        total_amount = sum(rfq.amount_total for rfq in current_rfqs)
        avg_response_time = sum((rfq.date_approve - rfq.date_order).days for rfq in current_rfqs if rfq.date_approve) / len(current_rfqs) if current_rfqs else 0

        # Get previous period data
        previous_rfqs = self.env['purchase.order'].search(previous_domain)
        previous_total_rfqs = len(previous_rfqs)
        previous_total_amount = sum(rfq.amount_total for rfq in previous_rfqs)
        previous_avg_response = sum((rfq.date_approve - rfq.date_order).days for rfq in previous_rfqs if rfq.date_approve) / len(previous_rfqs) if previous_rfqs else 0

        # Calculate product breakdown with categories
        product_data = {}
        categories = set()
        for rfq in current_rfqs:
            for line in rfq.order_line:
                product = line.product_id
                category = product.categ_id.name
                categories.add(category)
                
                product_name = product.name
                if product_name in product_data:
                    product_data[product_name].update({
                        "quantity": product_data[product_name]["quantity"] + line.product_qty,
                        "amount": product_data[product_name]["amount"] + line.price_subtotal,
                    })
                else:
                    product_data[product_name] = {
                        "quantity": line.product_qty,
                        "amount": line.price_subtotal,
                        "image": product.image_1920.decode("utf-8") if product.image_1920 else False,
                        "category": category,
                        "unit_price": line.price_unit,
                    }

        # Convert product data to list
        product_breakdown = [
            {
                "name": name,
                "quantity": data["quantity"],
                "amount": data["amount"],
                "image": data["image"],
                "category": data["category"],
                "unit_price": data["unit_price"],
            }
            for name, data in product_data.items()
        ]

        # Category-wise totals
        category_totals = {}
        for product in product_breakdown:
            category = product["category"]
            if category in category_totals:
                category_totals[category] += product["amount"]
            else:
                category_totals[category] = product["amount"]

        result = {
            "totalRFQs": total_rfqs,
            "totalAmount": total_amount,
            "avgResponseTime": round(avg_response_time, 1),
            "productBreakdown": product_breakdown,
            "categoryTotals": category_totals,
            "previousRFQs": previous_total_rfqs,
            "previousAmount": previous_total_amount,
            "previousAvgResponse": round(previous_avg_response, 1),
            "categories": list(categories)
        }

        return result