import pytest
import yaml

from click.testing import CliRunner
from pathlib import Path
from email.parser import Parser

from esi_lease_notifier.cli import main


@pytest.fixture
def configfile(tempdir: Path, smtp_sink_unix: tuple[Path, Path]):
    _, socketpath = smtp_sink_unix
    path = tempdir / "config.yaml"
    config = {
        "esi_lease_notifier": {
            "email": {
                "smtp_server": f"{socketpath}",
                "smtp_from": "test@example.com",
            },
            "idp": "tests.fakes.FakeIdp",
        }
    }
    with path.open("w") as fd:
        fd.write(yaml.safe_dump(config))

    return path


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_cli(
    configfile: str,
    templates: str,
    runner: CliRunner,
    smtp_sink_unix: tuple[Path, Path],
):
    dumppath, _ = smtp_sink_unix
    res = runner.invoke(main, ["-t", templates, "-c", configfile])
    assert res.exit_code == 0

    with dumppath.open() as fd:
        data = fd.read()

    parser = Parser()
    raw_msgs = data.split("---MESSAGE---\n")
    parsed_msgs = [parser.parsestr(msg) for msg in raw_msgs[1:]]

    assert len(parsed_msgs) == 2
    assert set(parsed_msgs[0]["to"].split(",")) == {
        "alice@example.com",
        "bob@example.com",
    }
    assert parsed_msgs[1]["to"] == "bob@example.com"


def test_cli_filters(
    configfile: str,
    templates: str,
    runner: CliRunner,
    smtp_sink_unix: tuple[Path, Path],
):
    dumppath, _ = smtp_sink_unix
    res = runner.invoke(
        main, ["-t", templates, "-c", configfile, "-f", "expires=daysleft:4"]
    )
    assert res.exit_code == 0

    with dumppath.open() as fd:
        data = fd.read()

    parser = Parser()
    raw_msgs = data.split("---MESSAGE---\n")
    parsed_msgs = [parser.parsestr(msg) for msg in raw_msgs[1:]]

    assert len(parsed_msgs) == 1
    assert parsed_msgs[0]["to"] == "bob@example.com"


def test_cli_dryrun(
    configfile: str,
    templates: str,
    runner: CliRunner,
    smtp_sink_unix: tuple[Path, Path],
):
    dumppath, _ = smtp_sink_unix
    res = runner.invoke(
        main,
        ["-t", templates, "-c", configfile, "-n"],
    )
    assert res.exit_code == 0
    assert not dumppath.exists()
