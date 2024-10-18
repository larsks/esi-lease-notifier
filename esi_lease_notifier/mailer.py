import smtplib
import logging

from typing import Protocol
from email.mime.multipart import MIMEMultipart

from .models import EmailTLSOption

LOG = logging.getLogger(__name__)


class MailerProtocol(Protocol):
    def send_message(self, msg: MIMEMultipart) -> None: ...


class SmtpMailer:
    def __init__(
        self,
        smtp_from: str,
        smtp_server: str = "localhost",
        smtp_port: int = 25,
        smtp_tls: EmailTLSOption = EmailTLSOption.EMAIL_TLS_NONE,
        smtp_username: str | None = None,
        smtp_password: str | None = None,
    ):
        if smtp_server.startswith("/"):
            smtp_class = smtplib.LMTP
        elif smtp_tls == EmailTLSOption.EMAIL_TLS_SSL:
            smtp_class = smtplib.SMTP_SSL
        else:
            smtp_class = smtplib.SMTP

        self.smtp_from = smtp_from
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_tls = smtp_tls
        self.smtp_class = smtp_class
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password

    def send_message(self, msg: MIMEMultipart) -> None:
        with self.smtp_class(self.smtp_server, self.smtp_port) as mailer:
            if self.smtp_tls == EmailTLSOption.EMAIL_TLS_STARTTLS:
                mailer.starttls()

            if self.smtp_username is not None and self.smtp_password is not None:
                mailer.login(self.smtp_username, self.smtp_password)

            LOG.info("sending mail to %s", msg["to"])
            mailer.send_message(msg)
