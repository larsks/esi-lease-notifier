import pytest
import random
import string

from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from esi_lease_notifier.mailer import SmtpMailer
from esi_lease_notifier.models import EmailConfiguration


def test_smtp_mailer(tempdir, smtp_sink):
    dumppath, socketpath = smtp_sink
    randomstring = "".join(random.sample(string.ascii_letters + string.digits, 10))
    m = SmtpMailer(
        EmailConfiguration(smtp_server=f"{socketpath}", smtp_from="test@example.com")
    )

    msg = MIMEMultipart()
    msg.attach(MIMEText(f"This is a test: {randomstring}", "plain"))
    msg["From"] = "test@example.com"
    msg["To"] = "alice@example.com"
    msg["Subject"] = "test message"

    m.send_message(msg)

    with dumppath.open() as fd:
        assert f"This is a test: {randomstring}" in fd.read()
