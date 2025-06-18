# -*- coding: utf-8 -*-
{
    'name': "Parche pagos en grupos",

    'summary': """
        Parche para corregir la conciliación de pagos en grupos""",

    'description': """
        Este módulo corrige el comportamiento de conciliación de pagos en grupos,
        asegurando que los pagos se concilien correctamente con las facturas y líneas de crédito.
    """,

    'author': "GonzaOdoo",
    'website': "https://github.com/GonzaOdoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account-payment-group'],

}