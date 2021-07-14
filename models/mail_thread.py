# -*- coding: utf-8 -*-

import logging

import threading

from odoo import _, api, exceptions, registry, SUPERUSER_ID

from odoo.tools.misc import split_every
from odoo.addons.mail.models.mail_thread import MailThread

_logger = logging.getLogger(__name__)

def _notify_record_by_email(self, message, recipients_data, msg_vals=False,
                            model_description=False, mail_auto_delete=True, check_existing=False,
                            force_send=True, send_after_commit=True, **kwargs):
    """ Override this method to make email send for notification_type = email or both """
    partners_data = [r for r in recipients_data['partners'] if r['notif'] == 'email' or 'both']
    if not partners_data:
        return True

    model = msg_vals.get('model') if msg_vals else message.model
    model_name = model_description or (self._fallback_lang().env['ir.model']._get(
        model).display_name if model else False)  # one query for display name
    recipients_groups_data = self._notify_classify_recipients(partners_data, model_name)

    if not recipients_groups_data:
        return True
    force_send = self.env.context.get('mail_notify_force_send', force_send)

    template_values = self._notify_prepare_template_context(message, msg_vals,
                                                            model_description=model_description)  # 10 queries

    email_layout_xmlid = msg_vals.get(
        'email_layout_xmlid') if msg_vals else message.email_layout_xmlid
    template_xmlid = email_layout_xmlid if email_layout_xmlid else 'mail.message_notification_email'
    try:
        base_template = self.env.ref(template_xmlid, raise_if_not_found=True).with_context(
            lang=template_values['lang'])  # 1 query
    except ValueError:
        _logger.warning(
            'QWeb template %s not found when sending notification emails. Sending without layouting.' % (
                template_xmlid))
        base_template = False

    mail_subject = message.subject or (
                message.record_name and 'Re: %s' % message.record_name)  # in cache, no queries
    # prepare notification mail values
    base_mail_values = {
        'mail_message_id': message.id,
        'mail_server_id': message.mail_server_id.id,
        # 2 query, check acces + read, may be useless, Falsy, when will it be used?
        'auto_delete': mail_auto_delete,
        # due to ir.rule, user have no right to access parent message if message is not published
        'references': message.parent_id.sudo().message_id if message.parent_id else False,
        'subject': mail_subject,
    }
    base_mail_values = self._notify_by_email_add_values(base_mail_values)

    Mail = self.env['mail.mail'].sudo()
    emails = self.env['mail.mail'].sudo()

    # loop on groups (customer, portal, user,  ... + model specific like group_sale_salesman)
    notif_create_values = []
    recipients_max = 50
    for recipients_group_data in recipients_groups_data:
        # generate notification email content
        recipients_ids = recipients_group_data.pop('recipients')
        render_values = {**template_values, **recipients_group_data}
        # {company, is_discussion, lang, message, model_description, record, record_name, signature, subtype, tracking_values, website_url}
        # {actions, button_access, has_button_access, recipients}

        if base_template:
            mail_body = base_template._render(render_values, engine='ir.qweb',
                                              minimal_qcontext=True)
        else:
            mail_body = message.body
        mail_body = self.env['mail.render.mixin']._replace_local_links(mail_body)

        # create email
        for recipients_ids_chunk in split_every(recipients_max, recipients_ids):
            recipient_values = self._notify_email_recipient_values(recipients_ids_chunk)
            email_to = recipient_values['email_to']
            recipient_ids = recipient_values['recipient_ids']

            create_values = {
                'body_html': mail_body,
                'subject': mail_subject,
                'recipient_ids': [(4, pid) for pid in recipient_ids],
            }
            if email_to:
                create_values['email_to'] = email_to
            create_values.update(
                base_mail_values)  # mail_message_id, mail_server_id, auto_delete, references, headers
            email = Mail.create(create_values)

            if email and recipient_ids:
                tocreate_recipient_ids = list(recipient_ids)
                if check_existing:
                    existing_notifications = self.env['mail.notification'].sudo().search([
                        ('mail_message_id', '=', message.id),
                        ('notification_type', '=', 'email'),
                        ('res_partner_id', 'in', tocreate_recipient_ids)
                    ])
                    if existing_notifications:
                        tocreate_recipient_ids = [rid for rid in recipient_ids if
                                                  rid not in existing_notifications.mapped(
                                                      'res_partner_id.id')]
                        existing_notifications.write({
                            'notification_status': 'ready',
                            'mail_id': email.id,
                        })
                notif_create_values += [{
                    'mail_message_id': message.id,
                    'res_partner_id': recipient_id,
                    'notification_type': 'email',
                    'mail_id': email.id,
                    'is_read': True,  # discard Inbox notification
                    'notification_status': 'ready',
                } for recipient_id in tocreate_recipient_ids]
            emails |= email

    if notif_create_values:
        self.env['mail.notification'].sudo().create(notif_create_values)

    # NOTE:
    #   1. for more than 50 followers, use the queue system
    #   2. do not send emails immediately if the registry is not loaded,
    #      to prevent sending email during a simple update of the database
    #      using the command-line.
    test_mode = getattr(threading.currentThread(), 'testing', False)
    if force_send and len(emails) < recipients_max and (not self.pool._init or test_mode):
        # unless asked specifically, send emails after the transaction to
        # avoid side effects due to emails being sent while the transaction fails
        if not test_mode and send_after_commit:
            email_ids = emails.ids
            dbname = self.env.cr.dbname
            _context = self._context

            @self.env.cr.postcommit.add
            def send_notifications():
                db_registry = registry(dbname)
                with api.Environment.manage(), db_registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, _context)
                    env['mail.mail'].browse(email_ids).send()
        else:
            emails.send()

    return True

def _notify_record_by_inbox(self, message, recipients_data, msg_vals=False, **kwargs):
    """ Override this method to make inbox notification for notification_type == both """
    channel_ids = [r['id'] for r in recipients_data['channels']]
    if channel_ids:
        message.write({'channel_ids': [(6, 0, channel_ids)]})

    inbox_pids = [r['id'] for r in recipients_data['partners'] if r['notif'] == 'inbox' or 'both']
    if inbox_pids:
        notif_create_values = [{
            'mail_message_id': message.id,
            'res_partner_id': pid,
            'notification_type': 'inbox',
            'notification_status': 'sent',
        } for pid in inbox_pids]
        self.env['mail.notification'].sudo().create(notif_create_values)

    bus_notifications = []
    if inbox_pids or channel_ids:
        message_format_values = False
        if inbox_pids:
            message_format_values = message.message_format()[0]
            for partner_id in inbox_pids:
                bus_notifications.append(
                    [(self._cr.dbname, 'ir.needaction', partner_id), dict(message_format_values)])
        if channel_ids:
            channels = self.env['mail.channel'].sudo().browse(channel_ids)
            bus_notifications += channels._channel_message_notifications(message,
                                                                         message_format_values)
            # Message from mailing channel should not make a notification in Odoo for users
            # with notification "Handled by Email", but web client should receive the message.
            # To do so, message is still sent from longpolling, but channel is marked as read
            # in order to remove notification.
            for channel in channels.filtered(lambda c: c.email_send):
                users = channel.channel_partner_ids.mapped('user_ids')
                for user in users.filtered(lambda u: u.notification_type == 'email'):
                    channel.with_user(user).channel_seen(message.id)

    if bus_notifications:
        self.env['bus.bus'].sudo().sendmany(bus_notifications)

MailThread._notify_record_by_email = _notify_record_by_email
MailThread._notify_record_by_inbox = _notify_record_by_inbox