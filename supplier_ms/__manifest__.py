# -*- coding: utf-8 -*-
{
    'name': "Supplier Management System",
    'summary': """
        Manage supplier registration, RFP, and quotations
    """,
    'description': """
        Complete supplier management system including:
        - Supplier Registration
        - RFP Management
        - Quotation Submission
        - Approval Workflow
    """,
    'author': "Your Company",
    'website': "https://www.yourcompany.com",
    'category': 'Purchase',
    'version': '1.0',
    'depends': [
        'base',
        'mail',
        'purchase',
        'portal',
        'hr',
        'web',
        'website',
    ],
    'data': [
        'security/supplier_ms_security.xml',
        'security/ir.model.access.csv',

        # Models and views

        # Data
        'data/ir_sequence_data.xml',

        # Views
        'views/supplier_application_view.xml',
        'views/purchase_rfp_views.xml',
        'views/portal_rfp_templates.xml',
        'views/res_partner_view.xml',
        'views/purchase_order_views.xml',
        'views/portal_template.xml',
        'views/portal_menus.xml',
        'views/mail_blacklist_views.xml',
        'views/auth_signup_login_templates.xml',

        # Reports
        'reports/rfp_report_templates.xml',

        # Wizards
        'wizards/rfp_report_wizard_view.xml',

        # Menu
        'views/menus.xml',
    ],
    'demo': [
        'demo/supplier_application_demo.xml',
        'demo/purchase_rfp_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },

'assets': {
    'web.assets_backend': [
        # Load Chart.js from CDN
        'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js',
        
        # Load styles
        'supplier_ms/static/src/components/supplier_dashboard.scss',
        
        # Load templates
        'supplier_ms/static/src/components/kpi_card/kpi_card.xml',
        'supplier_ms/static/src/components/chart_renderer/chart_renderer.xml',
        'supplier_ms/static/src/components/supplier_dashboard.xml',
        
        # Load JS files
        'supplier_ms/static/src/components/kpi_card/kpi_card.js',
        'supplier_ms/static/src/components/chart_renderer/chart_renderer.js',
        'supplier_ms/static/src/components/supplier_dashboard.js',
        'supplier_ms/static/src/js/supplier_dashboard_action.js',
        'supplier_ms/static/demo/*',
    ],
},

}
