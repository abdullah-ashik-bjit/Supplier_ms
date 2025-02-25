from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import io
import xlsxwriter
import base64
from odoo.tools import date_utils
import logging

_logger = logging.getLogger(__name__)


class RFPReportWizard(models.TransientModel):
    _name = 'rfp.report.wizard'
    _description = 'RFP Report Generator'

    supplier_id = fields.Many2one(
        'res.partner', 
        string='Supplier',
        required=True,
        domain=[('supplier_rank', '>', 0)],
        options={'no_create': True, 'no_open': True}
    )
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.context_today
    )
    end_date = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.context_today
    )

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError(_("Start date must be before or equal to end date."))

    def _get_report_values(self, docids, data=None):
        """Prepare the report data"""
        docs = self.browse(docids)
        
        # Debug logging for initial parameters
        _logger.info("Report Parameters:")
        _logger.info("- Supplier ID: %s", self.supplier_id.id)
        _logger.info("- Supplier Name: %s", self.supplier_id.name)
        _logger.info("- Start Date: %s", self.start_date)
        _logger.info("- End Date: %s", self.end_date)
        
        # First, find all RFPs for this supplier regardless of dates and state
        all_rfps = self.env['purchase.rfp'].search([
            ('approved_supplier_id', '=', self.supplier_id.id)
        ])
        _logger.info("All RFPs for supplier: %s", all_rfps.mapped(lambda r: {
            'name': r.name,
            'state': r.state,
            'required_date': r.required_date,
            'supplier': r.approved_supplier_id.name
        }))
        
        # Then apply our specific domain
        domain = [
            ('approved_supplier_id', '=', self.supplier_id.id),
            ('required_date', '>=', self.start_date),
            ('required_date', '<=', self.end_date),
            ('state', '=', 'accepted')
        ]
        
        _logger.info("Search Domain: %s", domain)
        
        rfps = self.env['purchase.rfp'].search(domain)
        
        # Debug logging for found RFPs
        _logger.info("Found RFPs after filtering:")
        for rfp in rfps:
            _logger.info("RFP: %s", {
                'name': rfp.name,
                'state': rfp.state,
                'required_date': rfp.required_date,
                'supplier': rfp.approved_supplier_id.name
            })
        
        if not rfps:
            # Log more details about why no RFPs were found
            _logger.warning("No RFPs found matching criteria. Checking individual conditions:")
            
            # Check each condition separately
            supplier_rfps = self.env['purchase.rfp'].search([
                ('approved_supplier_id', '=', self.supplier_id.id)
            ])
            _logger.warning("RFPs for supplier: %s", supplier_rfps.mapped('name'))
            
            date_rfps = supplier_rfps.filtered(
                lambda r: r.required_date >= self.start_date and r.required_date <= self.end_date
            )
            _logger.warning("RFPs within date range: %s", date_rfps.mapped('name'))
            
            accepted_rfps = date_rfps.filtered(lambda r: r.state == 'accepted')
            _logger.warning("Accepted RFPs: %s", accepted_rfps.mapped('name'))
            
            raise ValidationError(_(
                "No accepted RFPs found for supplier '%s' between %s and %s\n"
                "Please verify:\n"
                "- The supplier has RFPs assigned\n"
                "- The RFPs are in 'accepted' state\n"
                "- The required dates fall within the selected date range"
            ) % (self.supplier_id.name, self.start_date, self.end_date))

        products_data = []
        for rfp in rfps:
            # Get the selected purchase order for this RFP
            purchase_order = rfp.selected_po_id
            if purchase_order:
                for line in purchase_order.order_line:
                    products_data.append({
                        'name': line.product_id.name,
                        'quantity': line.product_qty,
                        'unit_price': line.price_unit,
                        'delivery_charges': line.delivery_charges,
                        'subtotal': line.price_subtotal,
                    })

        company = self.env.company
        return {
            'doc_ids': docids,
            'doc_model': 'rfp.report.wizard',
            'docs': docs,
            'company': {
                'id': company.id,
                'name': company.name,
                'logo': company.logo,
                'email': company.email,
                'phone': company.phone,
                'address': company.street,
            },
            'supplier': {
                'name': self.supplier_id.name,
                'email': self.supplier_id.email,
                'phone': self.supplier_id.phone,
                'address': self.supplier_id.street,
                'vat': self.supplier_id.vat,
                'bank': {
                    'name': self.supplier_id.bank_ids and self.supplier_id.bank_ids[0].bank_id.name or '',
                    'acc_name': self.supplier_id.bank_ids and self.supplier_id.bank_ids[0].acc_holder_name or '',
                    'acc_number': self.supplier_id.bank_ids and self.supplier_id.bank_ids[0].acc_number or '',
                    'iban': self.supplier_id.bank_ids and self.supplier_id.bank_ids[0].iban or '',
                    'swift': self.supplier_id.bank_ids and self.supplier_id.bank_ids[0].bank_id.bank_swift_code or '',
                }
            },
            'rfps': [{
                'number': rfp.name,
                'date': rfp.create_date.strftime('%d/%m/%Y') if rfp.create_date else '',
                'required_date': rfp.required_date.strftime('%d/%m/%Y') if rfp.required_date else '',
                'total_amount': rfp.selected_po_id.amount_total if rfp.selected_po_id else 0.0,
            } for rfp in rfps],
            'products': products_data,
        }

    def action_preview_report(self):
        """Generate HTML preview of the report"""
        # Get the report values
        data = self._get_report_values(self.ids)
        
        # Debug log the data being passed to the template
        _logger.info("Report Data:")
        _logger.info("Company: %s", data.get('company'))
        _logger.info("Supplier: %s", data.get('supplier'))
        _logger.info("RFPs: %s", data.get('rfps'))
        _logger.info("Products: %s", data.get('products'))
        
        # Return the report action with the data
        return self.env.ref('supplier_ms.action_report_rfp').with_context(
            landscape=True
        ).report_action(self, data=data)

    def action_export_excel(self):
        # Logic to generate Excel report
        return self._generate_excel_report()

    def _generate_excel_report(self):
        """Generate Excel report with professional styling"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('RFP Report')

        # Verify company logo
        if not self.env.company.logo:
            raise ValidationError(_("Please add a company logo before generating the report."))

        # Modern color scheme
        primary_color = '#1a73e8'  # Modern blue
        secondary_color = '#f8f9fa'  # Light gray
        border_color = '#dadce0'  # Subtle border
        total_row_color = '#e8f0fe'  # Light blue for totals

        # Set column widths
        worksheet.set_column('A:A', 18)  # RFP/Product Number
        worksheet.set_column('B:D', 25)  # Dates and Names
        worksheet.set_column('E:H', 15)  # Numeric columns

        # Common formats
        title_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 16,
            'bold': True,
            'font_color': primary_color,
            'align': 'left',
            'valign': 'vcenter',
        })

        header_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 11,
            'bold': True,
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': primary_color,
            'border': 1,
            'border_color': border_color,
        })

        section_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 12,
            'bold': True,
            'font_color': primary_color,
            'align': 'left',
            'valign': 'vcenter',
            'bg_color': secondary_color,
        })

        info_label_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'bold': True,
            'align': 'right',
            'valign': 'vcenter',
        })

        info_value_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'align': 'left',
            'valign': 'vcenter',
        })

        date_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'align': 'center',
            'num_format': 'dd/mm/yyyy',
            'border': 1,
            'border_color': border_color,
        })

        number_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'align': 'right',
            'num_format': '#,##0.00',
            'border': 1,
            'border_color': border_color,
        })

        # SECTION 1: Company Logo and Supplier Information
        # Insert company logo
        logo_data = base64.b64decode(self.env.company.logo)
        logo_path = '/tmp/company_logo.png'
        with open(logo_path, 'wb') as f:
            f.write(logo_data)
        worksheet.insert_image('A1', logo_path, {'x_scale': 0.5, 'y_scale': 0.5})

        # Supplier Information
        current_row = 1
        worksheet.merge_range(f'C{current_row}:H{current_row}', self.supplier_id.name, title_format)
        current_row += 2

        # Supplier Details Table
        supplier_info = [
            ('Email', self.supplier_id.email or ''),
            ('Phone', self.supplier_id.phone or ''),
            ('Address', self.supplier_id.street or ''),
            ('TIN', self.supplier_id.vat or ''),
            ('Bank Name', self.supplier_id.bank_ids and self.supplier_id.bank_ids[0].bank_id.name or ''),
            ('Account Name', self.supplier_id.bank_ids and self.supplier_id.bank_ids[0].acc_holder_name or ''),
            ('Account Number', self.supplier_id.bank_ids and self.supplier_id.bank_ids[0].acc_number or ''),
            ('IBAN', self.supplier_id.bank_ids and self.supplier_id.bank_ids[0].iban or ''),
            ('SWIFT Code', self.supplier_id.bank_ids and self.supplier_id.bank_ids[0].bank_id.bank_swift_code or '')
        ]

        for label, value in supplier_info:
            worksheet.write(current_row, 2, label, info_label_format)
            worksheet.merge_range(current_row, 3, current_row, 7, value, info_value_format)
            current_row += 1

        current_row += 2

        # SECTION 2: RFP Summary Table
        worksheet.merge_range(f'A{current_row}:H{current_row}', 'RFP Summary', section_format)
        current_row += 1

        # RFP Table Headers
        headers = ['RFP Number', 'Date', 'Required Date', 'Total Amount']
        for col, header in enumerate(headers):
            worksheet.write(current_row, col, header, header_format)
        current_row += 1

        # Get RFPs data
        domain = [
            ('approved_supplier_id', '=', self.supplier_id.id),
            ('required_date', '>=', self.start_date),
            ('required_date', '<=', self.end_date),
            ('state', '=', 'accepted')
        ]
        rfps = self.env['purchase.rfp'].search(domain)

        if not rfps:
            raise ValidationError(_(
                "No accepted RFPs found for supplier '%s' between %s and %s"
            ) % (self.supplier_id.name, self.start_date, self.end_date))

        # Write RFP data
        rfp_total = 0
        for rfp in rfps:
            worksheet.write(current_row, 0, rfp.name, info_value_format)
            worksheet.write(current_row, 1, rfp.create_date, date_format)
            worksheet.write(current_row, 2, rfp.required_date, date_format)
            amount = rfp.selected_po_id.amount_total if rfp.selected_po_id else 0.0
            worksheet.write(current_row, 3, amount, number_format)
            rfp_total += amount
            current_row += 1

        # Write RFP Total
        worksheet.merge_range(current_row, 0, current_row, 2, 'Net Amount', header_format)
        worksheet.write(current_row, 3, rfp_total, number_format)
        current_row += 2

        # SECTION 3: Product Summary Table
        worksheet.merge_range(f'A{current_row}:H{current_row}', 'Product Summary', section_format)
        current_row += 1

        # Product Table Headers
        headers = ['Product', 'Total Quantity', 'Average Unit Price', 'Total Delivery Charges', 'Total Amount']
        for col, header in enumerate(headers):
            worksheet.write(current_row, col, header, header_format)
        current_row += 1

        # Group products and calculate totals
        product_totals = {}
        for rfp in rfps:
            po = rfp.selected_po_id
            if po:
                for line in po.order_line:
                    product = line.product_id
                    if product not in product_totals:
                        product_totals[product] = {
                            'qty': 0,
                            'price_total': 0,
                            'delivery_total': 0,
                            'amount_total': 0,
                            'price_count': 0
                        }
                    product_totals[product]['qty'] += line.product_qty
                    product_totals[product]['price_total'] += line.price_unit
                    product_totals[product]['delivery_total'] += line.delivery_charges
                    product_totals[product]['amount_total'] += line.price_subtotal + line.delivery_charges
                    product_totals[product]['price_count'] += 1

        # Write product summary
        grand_total = 0
        for product, totals in product_totals.items():
            worksheet.write(current_row, 0, product.name, info_value_format)
            worksheet.write(current_row, 1, totals['qty'], number_format)
            avg_price = totals['price_total'] / totals['price_count'] if totals['price_count'] > 0 else 0
            worksheet.write(current_row, 2, avg_price, number_format)
            worksheet.write(current_row, 3, totals['delivery_total'], number_format)
            worksheet.write(current_row, 4, totals['amount_total'], number_format)
            grand_total += totals['amount_total']
            current_row += 1

        # Write Product Total
        worksheet.merge_range(current_row, 0, current_row, 3, 'Total Amount', header_format)
        worksheet.write(current_row, 4, grand_total, number_format)
        current_row += 2

        # SECTION 4: Company Footer
        footer_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'align': 'left',
            'valign': 'vcenter',
            'font_color': '#666666',
        })

        company = self.env.company
        worksheet.merge_range(f'A{current_row}:H{current_row}', company.name, footer_format)
        current_row += 1
        if company.email:
            worksheet.merge_range(f'A{current_row}:H{current_row}', f'Email: {company.email}', footer_format)
            current_row += 1
        if company.phone:
            worksheet.merge_range(f'A{current_row}:H{current_row}', f'Phone: {company.phone}', footer_format)
            current_row += 1
        if company.street:
            worksheet.merge_range(f'A{current_row}:H{current_row}', f'Address: {company.street}', footer_format)

        # Final touches
        worksheet.hide_gridlines(2)
        worksheet.set_landscape()
        worksheet.fit_to_pages(1, 0)
        worksheet.set_margins(left=0.5, right=0.5, top=0.5, bottom=0.5)

        workbook.close()
        output.seek(0)
        
        # Generate Excel file name
        filename = f'RFP_Report_{self.supplier_id.name}_{fields.Date.today()}.xlsx'
        
        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.getvalue()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}/{filename}?download=true',
            'target': 'self',
        }
