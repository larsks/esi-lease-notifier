import random
import string

from pathlib import Path

from esi_lease_notifier.models import Message
from esi_lease_notifier.mailer import SmtpMailer


def test_smtp_mailer(smtp_sink: tuple[Path, Path]):
    dumppath, socketpath = smtp_sink
    randomstring = "".join(random.sample(string.ascii_letters + string.digits, 10))
    mailer = SmtpMailer(smtp_server=f"{socketpath}", smtp_from="test@example.com")

    msg = Message(
        msg_from="test@example.com",
        recipients=["alice@example.com"],
        subject="test message",
        body_html=f"test html body {randomstring}",
        body_text=f"test text body {randomstring}",
    )

    mailer.send_message(msg.as_mime_multipart())

    with dumppath.open() as fd:
        content = fd.read()
        assert f"To: {msg.msg_to}" in content
        assert msg.body_html in content
        assert msg.body_text in content
