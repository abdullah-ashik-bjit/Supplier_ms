# -*- coding: utf-8 -*-
# from odoo import http


# class SupplierMs(http.Controller):
#     @http.route('/supplier_ms/supplier_ms', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/supplier_ms/supplier_ms/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('supplier_ms.listing', {
#             'root': '/supplier_ms/supplier_ms',
#             'objects': http.request.env['supplier_ms.supplier_ms'].search([]),
#         })

#     @http.route('/supplier_ms/supplier_ms/objects/<model("supplier_ms.supplier_ms"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('supplier_ms.object', {
#             'object': obj
#         })

