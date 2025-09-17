"""
class MailerSendApiEmailBackend and helpers

This class implements an EmailBackend compatible with Django.
The primary goal is to use API based email for Django logging and
user notification.
For now, we only consider text contents, no attachments, no cc, bcc, reply_to
or header information.
"""
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail import EmailMessage
from mailersend import MailerSendClient, EmailBuilder

class MailerSendApiEmailBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        apikey = settings.MAILERSEND_API_KEY
        ms = MailerSendClient(api_key=apikey)
        success_count = 0
        for email_message in email_messages:
            email = convert_email_to_mailersend(email_message)
            response = ms.emails.send(email)
            if response.success:
                success_count += 1
        return success_count


def convert_email_to_mailersend(email_message):
    email = (EmailBuilder()
             .from_email(email_message.from_email)
             .to_many([{'email': addr} for addr in email_message.to])
             .subject(email_message.subject)
             .text(email_message.body)
             .build())
    return email
