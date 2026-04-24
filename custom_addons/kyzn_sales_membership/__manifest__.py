{
    'name': "KYZN Sales",
    'summary': 'Module Odoo untuk sistem pencatatan sales terpusat KYZN.',
    'description': 'Module Odoo untuk memusatkan pencatatan, validasi, dan pelaporan penjualan membership pada PT Akademi Fambam Indonesia (KYZN).',
    'sequence': -100,
    'author': "Kelompok 06-K03",
    'category': 'Sales',
    'version': '1.0',
    'depends': ['base', 'sale'],
    'data': [
        'security/kyzn_groups.xml',
        'security/ir.model.access.csv',
        'security/kyzn_record_rules.xml',

        'views/menu_root.xml',

        'views/res_users_views.xml',
        'views/res_partner_views.xml',
        'views/membership_product_views.xml',

        'views/sales_order_tree.xml',
        'views/sales_order_search.xml',
        'views/sales_order_form.xml',
        'views/sale_order_form.xml',
        'views/sales_order_menu.xml',

        'views/validation_tree.xml',
        'views/validation_form.xml',
        'views/validation_search.xml',
        'views/validation_menu.xml',

        'views/report_graph.xml',
        'views/report_pivot.xml',
        'views/report_search.xml',
        'views/report_tree.xml',
        'views/report_menu.xml',

        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
