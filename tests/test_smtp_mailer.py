import pytest
import random
import string
import time
import subprocess
import tempfile

from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from esi_lease_notifier.mailer import SmtpMailer
from esi_lease_notifier.models import EmailConfiguration


@pytest.fixture
def tempdir():
    with tempfile.TemporaryDirectory() as _tempdir:
        yield Path(_tempdir)


@pytest.fixture
def smtp_sink(tempdir: Path):
    socketpath = tempdir / "smtp.sock"
    dumppath = tempdir / "smtp.dump"
    p = subprocess.Popen(
        [
            "smtp-sink",
            "-D",
            f"{dumppath}",
            f"unix:{socketpath}",
            "5",
        ]
    )

    while not socketpath.is_socket():
        time.sleep(0.1)
    yield (dumppath, socketpath)
    p.kill()
    p.wait()


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
