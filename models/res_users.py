# -*- coding: utf-8 -*-

from odoo import models, fields

class Users(models.Model):
    _inherit = 'res.users'

    # Add new option for notification type
    # Enable to send notification both in email and inbox
    notification_type = fields.Selection(selection_add=[('both', 'Handle in both Emails and '
                                                                 'Odoo')],
                                         ondelete={'both': lambda records: record.write({
                                             'notification_type': 'email'})}) # In case the
    # module is uninstalled, notification_type is set to email
