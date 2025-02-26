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
        """Generate Excel report matching HTML preview format exactly"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('RFP Report')

        # Styles matching HTML template with enhanced visibility
        styles = {
            'header': workbook.add_format({
                'font_name': 'Arial',
                'font_size': 16,
                'bold': True,
                'align': 'left',
                'valign': 'vcenter',
                'font_color': '#2C5282',  # Deeper blue for better visibility
                'bottom': 2,
                'bottom_color': '#4299E1'  # Bottom border for emphasis
            }),
            'card_header': workbook.add_format({
                'font_name': 'Arial',
                'font_size': 13,
                'bold': True,
                'align': 'left',
                'valign': 'vcenter',
                'bg_color': '#EBF8FF',  # Light blue background
                'font_color': '#2B6CB0',  # Dark blue text
                'border': 2,
                'border_color': '#90CDF4'  # Lighter blue border
            }),
            'label': workbook.add_format({
                'font_name': 'Arial',
                'font_size': 11,
                'bold': True,
                'align': 'left',
                'valign': 'vcenter',
                'font_color': '#4A5568',  # Dark gray for better contrast
                'bg_color': '#F7FAFC'  # Very light gray background
            }),
            'value': workbook.add_format({
                'font_name': 'Arial',
                'font_size': 11,
                'align': 'left',
                'valign': 'vcenter',
                'font_color': '#2D3748',  # Darker gray for values
                'bg_color': '#FFFFFF'  # White background
            }),
            'table_header': workbook.add_format({
                'font_name': 'Arial',
                'font_size': 11,
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#4299E1',  # Blue background
                'font_color': '#FFFFFF',  # White text
                'border': 1,
                'border_color': '#2B6CB0',  # Darker blue border
                'pattern': 1
            }),
            'table_cell': workbook.add_format({
                'font_name': 'Arial',
                'font_size': 11,
                'align': 'left',
                'valign': 'vcenter',
                'bg_color': '#FFFFFF',  # White background
                'border': 1,
                'border_color': '#CBD5E0',  # Light gray border
                'text_wrap': True
            }),
            'amount': workbook.add_format({
                'font_name': 'Arial',
                'font_size': 11,
                'align': 'right',
                'valign': 'vcenter',
                'bg_color': '#FFFFFF',  # White background
                'border': 1,
                'border_color': '#CBD5E0',  # Light gray border
                'num_format': '#,##0.00',
                'font_color': '#2D3748'  # Darker gray for numbers
            }),
            'total_row': workbook.add_format({
                'font_name': 'Arial',
                'font_size': 11,
                'bold': True,
                'align': 'right',
                'valign': 'vcenter',
                'bg_color': '#EBF8FF',  # Light blue background
                'border': 2,
                'border_color': '#90CDF4',  # Light blue border
                'num_format': '#,##0.00',
                'font_color': '#2C5282'  # Deep blue for emphasis
            }),
            'footer': workbook.add_format({
                'font_name': 'Arial',
                'font_size': 10,
                'align': 'center',
                'valign': 'vcenter',
                'font_color': '#4A5568',  # Dark gray
                'bg_color': '#F7FAFC',  # Very light gray background
                'top': 2,  # Use top instead of border_top
                'top_color': '#CBD5E0'  # Use top_color instead of border_top_color
            })
        }

        # Column widths - adjust first to accommodate logo
        worksheet.set_column('A:A', 12)  # Reduced logo column width
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 25)  # Title column wider
        worksheet.set_column('D:D', 20)
        worksheet.set_column('E:E', 15)
        worksheet.set_column('F:F', 15)

        current_row = 0

        # Header Section with Logo and Title
        company = self.env.company
        if company.logo:
            logo_data = base64.b64decode(company.logo)
            logo_path = '/tmp/company_logo.png'
            with open(logo_path, 'wb') as f:
                f.write(logo_data)
            
            # Set first two rows height for header section
            worksheet.set_row(0, 45)  # Reduced logo row height
            worksheet.set_row(1, 10)  # Spacing row
            
            # Insert logo with smaller size and adjusted positioning
            worksheet.insert_image(
                'A1', 
                logo_path, 
                {
                    'x_offset': 3,      # Reduced left offset
                    'y_offset': 3,      # Reduced top offset
                    'x_scale': 0.15,    # Reduced width to 15% of original
                    'y_scale': 0.15,    # Reduced height to 15% of original
                    'positioning': 1,    # Position image to move with cells
                    'object_position': 1 # Position object within the cell
                }
            )

        # Title and Date - adjust positioning
        worksheet.merge_range('C1:D1', 'RFP Report', styles['header'])
        worksheet.write('F1', fields.Date.today().strftime('%d/%m/%Y'), styles['value'])

        # Add spacing after header
        current_row = 3  # Start content after header section
        worksheet.set_row(2, 15)  # Add spacing row

        # Supplier Information Card starts at row 4
        worksheet.merge_range(f'A{current_row}:F{current_row}', 'Supplier Information', styles['card_header'])
        current_row += 1

        supplier = self.supplier_id
        supplier_info = [
            ('Company Name', supplier.name),
            ('Contact Information', ''),
            ('Email', supplier.email),
            ('Phone', supplier.phone),
            ('Address', supplier.street),
            ('Tax ID', supplier.vat)
        ]

        for label, value in supplier_info:
            if value:  # Skip empty values
                worksheet.write(current_row, 0, label, styles['label'])
                worksheet.merge_range(f'B{current_row+1}:F{current_row+1}', value, styles['value'])
                current_row += 1

        current_row += 2

        # RFP Table
        worksheet.merge_range(f'A{current_row}:F{current_row}', 'RFP Details', styles['card_header'])
        current_row += 1

        headers = ['RFP Number', 'Date', 'Required Date', 'Total Amount']
        for col, header in enumerate(headers):
            worksheet.write(current_row, col, header, styles['table_header'])
        current_row += 1

        domain = [
            ('approved_supplier_id', '=', self.supplier_id.id),
            ('required_date', '>=', self.start_date),
            ('required_date', '<=', self.end_date),
            ('state', '=', 'accepted')
        ]
        rfps = self.env['purchase.rfp'].search(domain)

        total_amount = 0
        for rfp in rfps:
            amount = rfp.selected_po_id.amount_total if rfp.selected_po_id else 0.0
            worksheet.write(current_row, 0, rfp.name, styles['table_cell'])
            worksheet.write(current_row, 1, rfp.create_date.strftime('%d/%m/%Y'), styles['table_cell'])
            worksheet.write(current_row, 2, rfp.required_date.strftime('%d/%m/%Y'), styles['table_cell'])
            worksheet.write(current_row, 3, amount, styles['amount'])
            total_amount += amount
            current_row += 1

        # Total row
        worksheet.write(current_row, 2, 'Total', styles['total_row'])
        worksheet.write(current_row, 3, total_amount, styles['total_row'])
        current_row += 2

        # Products Table
        worksheet.merge_range(f'A{current_row}:F{current_row}', 'Product Details', styles['card_header'])
        current_row += 1

        product_headers = ['Product', 'Quantity', 'Unit Price', 'Delivery Charges', 'Subtotal']
        for col, header in enumerate(product_headers):
            worksheet.write(current_row, col, header, styles['table_header'])
        current_row += 1

        for rfp in rfps:
            if rfp.selected_po_id:
                for line in rfp.selected_po_id.order_line:
                    worksheet.write(current_row, 0, line.product_id.name, styles['table_cell'])
                    worksheet.write(current_row, 1, line.product_qty, styles['table_cell'])
                    worksheet.write(current_row, 2, line.price_unit, styles['amount'])
                    worksheet.write(current_row, 3, line.delivery_charges, styles['amount'])
                    worksheet.write(current_row, 4, line.price_subtotal, styles['amount'])
                    current_row += 1

        # Footer
        current_row += 2
        footer_text = f"{company.name}\n{company.email}\n{company.phone}\n{company.street}"
        worksheet.merge_range(f'A{current_row}:F{current_row+3}', footer_text, styles['footer'])

        workbook.close()
        output.seek(0)

        # Create attachment
        filename = f'RFP_Report_{self.supplier_id.name}_{fields.Date.today()}.xlsx'
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
