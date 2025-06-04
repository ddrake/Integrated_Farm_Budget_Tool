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
from mailersend import emails

class MailerSendApiEmailBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        success_count = 0
        for email_message in email_messages:
            mailer, email = convert_email_to_mailersend(email_message)
            result = send(mailer, email)
            if result:
                success_count += 1
        return success_count


def convert_email_to_mailersend(email_message):
    mail_body = {}
    apikey = settings.MAILERSEND_API_KEY
    mailer = emails.NewEmail(apikey)
    mailer.set_mail_to([{'email': addr} for addr in email_message.to],
                      mail_body)
    mailer.set_subject(email_message.subject, mail_body)
    mailer.set_mail_from({'email': email_message.from_email}, mail_body)
    mailer.set_plaintext_content(email_message.body, mail_body)
    return mailer, mail_body
    
def send(mailer, mail_body):
    result = mailer.send(mail_body)
    return result[0] == '2'  # the HTTP status should start with 2. e.g. 200 or 202
