# -*- coding: utf-8 -*-
{
    'name': "custom_mail",

    'summary': """
        Custom config for mail in odoo aht erp""",

    'description': """
        Customizations include:
            - Force email_from value to only one specific email address instead of using the 
            sender email address
    """,

    'author': "linhhonblade",
    'website': "https://github.com/linhhonblade",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '14.0.1',

    # any module necessary for this one to work correctly
    'depends': ['mail'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
