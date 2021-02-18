# -*- coding: utf-8 -*-
# from odoo import http


# class CustomMail(http.Controller):
#     @http.route('/custom_mail/custom_mail/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_mail/custom_mail/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_mail.listing', {
#             'root': '/custom_mail/custom_mail',
#             'objects': http.request.env['custom_mail.custom_mail'].search([]),
#         })

#     @http.route('/custom_mail/custom_mail/objects/<model("custom_mail.custom_mail"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_mail.object', {
#             'object': obj
#         })
