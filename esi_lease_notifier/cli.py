import click
import io
import logging
import yaml

from typing import get_args

from .models import ConfigurationFile
from .models import ProjectFilter
from .models import ExpiresFilter
from .app import NotifierApp

LOG = logging.getLogger(__name__)
LOGLEVELS = ["WARNING", "INFO", "DEBUG"]
DEFAULT_CONFIG_FILE = "esi-lease-notifier.yaml"
AVAILABLE_FILTERS = [ProjectFilter, ExpiresFilter]


@click.command()
@click.option("--template-path", "-t", default="templates")
@click.option(
    "--config-file", "--config", "-c", default=DEFAULT_CONFIG_FILE, type=click.File()
)
@click.option("--verbosity", "-v", count=True)
@click.option("--filter", "-f", "filters", multiple=True)
def main(
    template_path: str,
    config_file: io.IOBase,
    filters: list[str],
    verbosity: int = 0,
):
    logLevel = LOGLEVELS[min(verbosity, len(LOGLEVELS))]
    logging.basicConfig(level=logLevel)
    with config_file:
        config = ConfigurationFile.model_validate(yaml.safe_load(config_file))

    app = NotifierApp(config.esi_lease_notifier, template_path=template_path)

    for filterspec in filters:
        kind, paramspec = filterspec.split("=")
        params = dict(param.split(":") for param in paramspec.split(","))
        for filterclass in AVAILABLE_FILTERS:
            thiskind: str = get_args(filterclass.model_fields["kind"].annotation)[0]
            if kind == thiskind:
                filter = filterclass.model_validate(params)
                break
        else:
            raise KeyError(f"unknown filter kind: {kind}")

        config.esi_lease_notifier.filters.append(filter)

    app.process_leases()
