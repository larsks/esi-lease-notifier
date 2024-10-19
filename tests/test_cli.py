import pytest
import yaml

from click.testing import CliRunner
from unittest import mock
from pathlib import Path

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
    with mock.patch("esi_lease_notifier.app.OpenstackIdp") as mock_idp:
        res = runner.invoke(main, ["-t", templates, "-c", configfile])
        assert res.exit_code == 0


def test_cli_filters(
    configfile: str,
    templates: str,
    runner: CliRunner,
    smtp_sink_unix: tuple[Path, Path],
):
    with mock.patch("esi_lease_notifier.app.OpenstackIdp") as mock_idp:
        res = runner.invoke(
            main, ["-t", templates, "-c", configfile, "-f", "expires=daysleft:4"]
        )
        assert res.exit_code == 0
