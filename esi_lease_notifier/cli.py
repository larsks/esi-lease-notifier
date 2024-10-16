import click
import io
import logging
import yaml

from .models import ConfigurationFile
from .app import NotifierApp
from .idp import OpenstackIdp

LOG = logging.getLogger(__name__)
LOGLEVELS = ["WARNING", "INFO", "DEBUG"]
DEFAULT_CONFIG_FILE = "esi-lease-notifier.yaml"


@click.command()
@click.option("--template-directory", "-d", "template_path", default="templates")
@click.option(
    "--config-file", "--config", "-c", default=DEFAULT_CONFIG_FILE, type=click.File()
)
@click.option("--verbosity", "-v", count=True)
def main(
    template_path: str,
    config_file: io.IOBase,
    verbosity: int = 0,
):
    logLevel = LOGLEVELS[min(verbosity, len(LOGLEVELS))]
    logging.basicConfig(level=logLevel)
    with config_file:
        config = ConfigurationFile.model_validate(yaml.safe_load(config_file))

    app = NotifierApp(config.esi_lease_notifier, template_path=template_path)

    app.process_leases()
