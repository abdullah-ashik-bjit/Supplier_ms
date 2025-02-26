from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from collections import OrderedDict
from odoo.osv.expression import OR, AND
import datetime
import logging
from odoo.tools import groupby as groupbyelem
from odoo.fields import Date
# from ..utils.mail_utils import send_rfq_submitted_notification

_logger = logging.getLogger(__name__)


class RFPPortal(CustomerPortal):
    _items_per_page = 10  # Make sure this is set

    @http.route(['/my/rfps', '/my/rfps/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_rfps(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None,
                       groupby=None, **kw):
        try:
            values = self._prepare_portal_layout_values()
            RFP = request.env['purchase.rfp'].sudo()

            # Get search options
            searchbar_values = self._get_rfp_searchbar_values()

            # Get domain with search
            domain = self._prepare_rfp_domain(search)

            # Default sort by value
            sortby = sortby if sortby in searchbar_values['sortings'] else 'date'
            order = searchbar_values['sortings'][sortby]['order']

            # Default filter by value
            filterby = filterby if filterby in searchbar_values['filters'] else 'all'
            domain += searchbar_values['filters'][filterby]['domain']

            # Default group by value
            groupby = groupby if groupby in searchbar_values['groupby'] else 'none'

            # Group by handling
            if groupby != 'none':
                order = f"{searchbar_values['groupby'][groupby]['input']}, {order}"

            # Count for pager
            rfp_count = RFP.search_count(domain)

            # Pager
            pager = portal_pager(
                url="/my/rfps",
                url_args={'sortby': sortby, 'filterby': filterby, 'groupby': groupby, 'search': search},
                total=rfp_count,
                page=page,
                step=self._items_per_page
            )

            # Fetch records
            rfps = RFP.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

            # Group records if needed
            if groupby != 'none':
                grouped_rfps = [RFP.concat(*g) for k, g in
                                groupbyelem(rfps, lambda r: r[searchbar_values['groupby'][groupby]['input']])]
            else:
                grouped_rfps = [rfps]

            values.update({
                'rfps': rfps,
                'grouped_rfps': grouped_rfps,
                'page_name': 'rfps',
                'pager': pager,
                'default_url': '/my/rfps',
                'searchbar_sortings': searchbar_values['sortings'],
                'searchbar_groupby': searchbar_values['groupby'],
                'searchbar_filters': searchbar_values['filters'],
                'sortby': sortby,
                'groupby': groupby,
                'filterby': filterby,
                'search': search
            })

            return request.render("supplier_ms.portal_my_rfps", values)
        except Exception as e:
            _logger.error("Error in portal_my_rfps: %s", str(e))
            return request.redirect('/my')

    @http.route(['/my/rfp/<int:rfp_id>'], type='http', auth="user", website=True)
    def portal_my_rfp(self, rfp_id, **kw):
        try:
            rfp = request.env['purchase.rfp'].sudo().browse(rfp_id)
            if not rfp.exists():
                return request.redirect('/my/rfps')

            # Check if coming from quotations list
            from_quotation_list = bool(
                request.httprequest.referrer and '/my/quotations' in request.httprequest.referrer
            )

            # Get specific quotation if coming from quotations list
            quotation = None
            if from_quotation_list:
                quotation_id = kw.get('quotation_id')  # Get quotation ID from URL parameter
                if quotation_id:
                    quotation = request.env['purchase.order'].sudo().browse(int(quotation_id))
                    # Verify this quotation belongs to this RFP and current user
                    if not quotation.exists() or quotation.rfp_id.id != rfp_id or quotation.partner_id != request.env.user.partner_id:
                        quotation = None
            
            if not quotation:
                # Fallback to getting the latest quotation for this RFP
                quotation = request.env['purchase.order'].sudo().search([
                    ('partner_id', '=', request.env.user.partner_id.id),
                    ('rfp_id', '=', rfp.id)
                ], limit=1)

            values = self._prepare_portal_layout_values()
            values.update({
                'rfp': rfp,
                'quotation': quotation,
                'page_name': 'rfp',
                'user': request.env.user,
                'datetime': datetime,
                'from_quotation_list': from_quotation_list,
            })
            return request.render("supplier_ms.portal_rfp_page", values)
        except Exception as e:
            _logger.error("Error in portal_my_rfp: %s", str(e))
            return request.redirect('/my/rfps')

    def _document_check_access(self, model_name, document_id, access_token=None):
        document = request.env[model_name].sudo().browse([document_id])
        document_sudo = document.sudo()
        if not document_sudo.exists():
            raise MissingError(_("This document does not exist."))

        if not document_sudo.can_access_from_portal():
            raise AccessError(_("You do not have access to this document."))
        return document_sudo

    @http.route(['/my/rfp/submit_quote'], type='http', auth="user", website=True, methods=['POST'])
    def submit_quotation(self, **post):
        """Handle quotation submission from portal"""
        try:
            rfp_id = int(post.get('rfp_id'))
            rfp = request.env['purchase.rfp'].browse(rfp_id)

            if not rfp.exists() or rfp.state != 'approved':
                return request.redirect('/my/rfps')

            # Create purchase order with context to indicate it's from portal
            po_vals = {
                'partner_id': request.env.user.partner_id.id,
                'rfp_id': rfp.id,
                'expected_delivery_date': post.get('expected_delivery_date'),
                'warranty_period': int(post.get('warranty_period')),
                'terms_conditions': post.get('terms_conditions'),
                'date_planned': post.get('expected_delivery_date'),
                'order_line': []
            }

            total_delivery_charges = 0.0
            # Add order lines with delivery charges
            for line in rfp.product_line_ids:
                unit_price = float(post.get(f'unit_price_{line.id}', 0))
                delivery_charges = float(post.get(f'delivery_charges_{line.id}', 0))
                total_delivery_charges += delivery_charges

                po_vals['order_line'].append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.description or line.product_id.display_name,
                    'product_qty': line.quantity,
                    'price_unit': unit_price,
                    'delivery_charges': delivery_charges,  # Add delivery charges to each line
                    'date_planned': post.get('expected_delivery_date'),
                }))

            # Create purchase order with portal context
            purchase_order = request.env['purchase.order'].with_context(from_portal=True).sudo().create(po_vals)

            # # Update total delivery charges
            # purchase_order.write({
            #     'delivery_charges': total_delivery_charges
            # })

            # Trigger recomputation of amounts
            purchase_order._amount_all()

            # Send notification email to reviewer
            template = request.env.ref('supplier_ms.email_template_rfq_submitted', raise_if_not_found=False)
            if template:
                template.sudo().with_context(
                    rfp_name=rfp.name,
                    supplier_name=request.env.user.partner_id.name
                ).send_mail(purchase_order.id, force_send=True)

            return request.redirect('/my/rfps?success=quote_submitted')

        except Exception as e:
            _logger.error("Error in submit_quotation: %s", str(e))
            return request.redirect(f'/my/rfp/{rfp_id}?error=submission_failed')

    # ----------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        if 'rfp_count' in counters:
            domain = [
                '|',
                ('state', '=', 'approved'),
                ('purchase_order_ids.partner_id', '=', partner.id)
            ]
            values['rfp_count'] = request.env['purchase.rfp'].sudo().search_count(domain)

        if 'quotation_count' in counters:
            values['quotation_count'] = request.env['purchase.order'].sudo().search_count([
                ('partner_id', '=', partner.id),
                ('rfp_id', '!=', False)
            ])

        if 'purchase_count' in counters:
            values['purchase_count'] = request.env['purchase.order'].sudo().search_count([
                ('partner_id', '=', partner.id)
            ])
        return values

    def _get_rfp_domain(self, search_in, search):
        domain = [('state', 'not in', ['draft', 'closed'])]  # Show RFPs until they are closed
        if search and search_in:
            if search_in == 'name':
                domain += [('name', 'ilike', search)]
            elif search_in == 'product':
                domain += [('product_line_ids.product_id.name', 'ilike', search)]
        return domain

    def _get_quotation_searchbar_values(self):
        return {
            'sortings': OrderedDict([
                ('date', {'label': _('Newest'), 'order': 'create_date desc', 'sequence': 1}),
                ('name', {'label': _('Reference'), 'order': 'name', 'sequence': 2}),
                ('amount', {'label': _('Amount'), 'order': 'amount_total desc', 'sequence': 3}),
            ]),
            'filters': OrderedDict([
                ('all', {'label': _('All'), 'domain': [], 'sequence': 1}),
                ('draft', {'label': _('Draft'), 'domain': [('state', '=', 'draft')], 'sequence': 2}),
                ('sent', {'label': _('Submitted'), 'domain': [('state', '=', 'sent')], 'sequence': 3}),
                ('purchase', {'label': _('Purchase Order'), 'domain': [('state', '=', 'purchase')], 'sequence': 4}),
                ('done', {'label': _('Done'), 'domain': [('state', '=', 'done')], 'sequence': 5}),
                ('cancel', {'label': _('Cancelled'), 'domain': [('state', '=', 'cancel')], 'sequence': 6}),
            ]),
            'groupby': OrderedDict([
                ('none', {'input': 'none', 'label': _('None'), 'sequence': 1}),
                ('status', {'input': 'state', 'label': _('Status'), 'sequence': 2}),
                ('rfp', {'input': 'rfp_id', 'label': _('RFP'), 'sequence': 3}),
            ])
        }

    def _prepare_quotation_domain(self, search=None, **kw):
        partner = request.env.user.partner_id
        # Base domain - show all quotations for this supplier
        domain = [
            ('partner_id', '=', partner.id),
            ('rfp_id', '!=', False),  # Only show RFP-related quotations
            # Include 'sent' state and remove 'submitted' (since 'sent' is the correct state after submission)
            ('state', 'in', ['draft', 'sent', 'purchase', 'done', 'cancel'])
        ]

        if search and search.strip():
            domain = AND([
                domain,
                ['|', '|', '|',
                 ('name', 'ilike', search.strip()),
                 ('rfp_id.name', 'ilike', search.strip()),
                 ('amount_total', 'ilike', search.strip()),
                 ('state', 'ilike', search.strip())
                ]
            ])
        return domain

    @http.route(['/my/quotations', '/my/quotations/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_quotations(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None,
                             search_in='all', groupby=None, **kw):
        try:
            values = self._prepare_portal_layout_values()
            partner = request.env.user.partner_id
            PurchaseOrder = request.env['purchase.order'].sudo()

            # Get search options
            searchbar_values = self._get_quotation_searchbar_values()

            # Get domain with search
            domain = self._prepare_quotation_domain(search)

            # Default sort by value
            sortby = sortby if sortby in searchbar_values['sortings'] else 'date'
            order = searchbar_values['sortings'][sortby]['order']

            # Default filter by value
            filterby = filterby if filterby in searchbar_values['filters'] else 'all'
            domain += searchbar_values['filters'][filterby]['domain']

            # Default group by value
            groupby = groupby if groupby in searchbar_values['groupby'] else 'none'

            # Group by handling
            if groupby != 'none':
                order = f"{searchbar_values['groupby'][groupby]['input']}, {order}"

            # Count for pager
            quotation_count = PurchaseOrder.search_count(domain)

            # Pager
            pager = portal_pager(
                url="/my/quotations",
                url_args={'sortby': sortby, 'filterby': filterby, 'groupby': groupby, 'search': search},
                total=quotation_count,
                page=page,
                step=self._items_per_page
            )

            # Fetch records with pager
            quotations = PurchaseOrder.search(
                domain,
                order=order,
                limit=self._items_per_page,
                offset=pager['offset']
            )

            values.update({
                'quotations': quotations,
                'page_name': 'my_quotations',
                'pager': pager,
                'default_url': '/my/quotations',
                'searchbar_sortings': searchbar_values['sortings'],
                'searchbar_groupby': searchbar_values['groupby'],
                'searchbar_filters': searchbar_values['filters'],
                'sortby': sortby,
                'groupby': groupby,
                'filterby': filterby,
                'search': search,
                'search_in': search_in,
                'searchbar_inputs': {
                    'all': {'input': 'all', 'label': _('Search in All')},
                    'reference': {'input': 'reference', 'label': _('Search in Reference')},
                    'amount': {'input': 'amount', 'label': _('Search in Amount')},
                },
            })

            return request.render("supplier_ms.portal_my_quotations", values)
        except Exception as e:
            _logger.error("Error in portal_my_quotations: %s", str(e))
            return request.redirect('/my')

    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        partner = request.env.user.partner_id

        # Update quotation count to include all RFP-related quotations
        values['quotation_count'] = request.env['purchase.order'].sudo().search_count([
            ('partner_id', '=', partner.id),
            ('rfp_id', '!=', False),
            ('state', 'in', ['draft', 'submitted', 'recommendation', 'approved', 'rejected', 'accepted'])
        ])

        values['rfp_count'] = request.env['purchase.rfp'].sudo().search_count([
            ('state', '=', 'approved')
        ])

        return values

    def _prepare_rfp_domain(self, search=None, **kw):
        domain = [('state', 'in', ['approved', 'recommendation', 'accepted', 'closed'])]

        if search:
            search_domain = [
                '|', '|', '|',
                ('name', 'ilike', search),
                ('description', 'ilike', search),
                ('product_line_ids.product_id.name', 'ilike', search),
                ('product_line_ids.description', 'ilike', search)
            ]
            domain = AND([domain, search_domain])

        return domain

    def _get_rfp_searchbar_values(self):
        return {
            'sortings': {
                'date': {'label': _('Newest'), 'order': 'create_date desc', 'sequence': 1},
                'name': {'label': _('Reference'), 'order': 'name', 'sequence': 2},
                'deadline': {'label': _('Deadline'), 'order': 'required_date', 'sequence': 3},
            },
            'groupby': {
                'none': {'input': 'none', 'label': _('None'), 'sequence': 1},
                'status': {'input': 'state', 'label': _('Status'), 'sequence': 2},
            },
            'filters': {
                'all': {'label': _('All'), 'domain': [], 'sequence': 1},
                'open': {'label': _('Open'), 'domain': [('state', '=', 'approved')], 'sequence': 2},
                'under_review': {'label': _('Under Review'), 'domain': [('state', '=', 'recommendation')],
                                 'sequence': 3},
                'accepted': {'label': _('Accepted'), 'domain': [('state', '=', 'accepted')], 'sequence': 4},
                'closed': {'label': _('Closed'), 'domain': [('state', '=', 'closed')], 'sequence': 5},
            }
        }