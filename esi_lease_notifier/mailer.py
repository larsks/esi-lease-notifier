import smtplib

from typing import Protocol
from email.mime.multipart import MIMEMultipart

from .models import EmailConfiguration
from .models import EmailTLSOption


class MailerProtocol(Protocol):
    def send_message(self, msg: MIMEMultipart) -> None: ...


class SmtpMailer:
    def __init__(self, config: EmailConfiguration):
        self.config = config

        if self.config.smtp_server.startswith("/"):
            smtpclass = smtplib.LMTP
        elif config.smtp_tls == EmailTLSOption.EMAIL_TLS_SSL:
            smtpclass = smtplib.SMTP_SSL
        else:
            smtpclass = smtplib.SMTP

        self.smtpclass = smtpclass

    def send_message(self, msg: MIMEMultipart) -> None:
        with self.smtpclass(self.config.smtp_server, self.config.smtp_port) as mailer:
            if self.config.smtp_tls == EmailTLSOption.EMAIL_TLS_STARTTLS:
                mailer.starttls()
            if self.config.smtp_username:
                mailer.login(config.smtp_username, config.smtp_password)

            mailer.send_message(msg)
