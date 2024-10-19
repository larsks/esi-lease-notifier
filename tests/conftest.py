import pytest
import subprocess
import tempfile
import time
import random
import smtplib

from pathlib import Path


@pytest.fixture
def tempdir():
    with tempfile.TemporaryDirectory() as _tempdir:
        yield Path(_tempdir)


@pytest.fixture
def smtp_sink_unix(tempdir: Path):
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


@pytest.fixture
def smtp_sink_tcp(tempdir: Path):
    dumppath = tempdir / "smtp.dump"
    port = random.randint(10000, 30000)
    p = subprocess.Popen(
        [
            "smtp-sink",
            "-D",
            f"{dumppath}",
            f"localhost:{port}",
            "5",
        ]
    )

    # Wait until the server is listening
    while True:
        try:
            with smtplib.SMTP("localhost", port=port):
                pass
        except ConnectionRefusedError:
            time.sleep(0.1)
            continue

        break

    yield (dumppath, port)
    p.kill()
    p.wait()


@pytest.fixture
def templates(tempdir: Path):
    tp = tempdir / "templates"
    tp.mkdir()

    with (tp / "subject.txt").open("w") as fd:
        fd.write("Test email about {{ project.name }}")

    with (tp / "body.txt").open("w") as fd:
        fd.write("{{ leases|tabulate }}")

    with (tp / "body.html").open("w") as fd:
        fd.write("{{ leases|tabulate(html=True) }}")

    return tp
