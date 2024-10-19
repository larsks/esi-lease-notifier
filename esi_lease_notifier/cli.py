import click
import io
import logging
import yaml
import importlib

from typing import get_args
from email.mime.multipart import MIMEMultipart

from esi_lease_notifier.idp import IdpProtocol
from esi_lease_notifier.mailer import MailerProtocol

from .models import ConfigurationFile
from .models import ProjectFilter
from .models import ExpiresFilter
from .app import NotifierApp

LOG = logging.getLogger(__name__)
LOGLEVELS = ["WARNING", "INFO", "DEBUG"]
DEFAULT_CONFIG_FILE = "esi-lease-notifier.yaml"
AVAILABLE_FILTERS = [ProjectFilter, ExpiresFilter]


class NullMailer:
    def send_message(self, msg: MIMEMultipart):  # pyright: ignore[reportUnusedParameter]
        pass


def load_class(qname: str):
    modulename, classname = qname.rsplit(".", 1)
    module = importlib.import_module(modulename)
    return getattr(module, classname)


@click.command()
@click.option("--template-path", "-t", default="templates")
@click.option(
    "--config-file", "--config", "-c", default=DEFAULT_CONFIG_FILE, type=click.File()
)
@click.option("--verbosity", "-v", count=True)
@click.option("--filter", "-f", "filters", multiple=True)
@click.option("--dryrun", "-n", is_flag=True, default=False, type=bool)
def main(
    template_path: str,
    config_file: io.IOBase,
    filters: list[str],
    verbosity: int = 0,
    dryrun: bool = False,
):
    logLevel = LOGLEVELS[min(verbosity, len(LOGLEVELS))]
    logging.basicConfig(level=logLevel)
    with config_file:
        config = ConfigurationFile.model_validate(
            yaml.safe_load(config_file)
        ).esi_lease_notifier

    mailer: MailerProtocol | None = None
    idp: IdpProtocol | None = None

    if config.mailer:
        mailer = load_class(config.mailer)()
    elif dryrun:
        mailer = NullMailer()

    if config.idp:
        idp = load_class(config.idp)()

    app = NotifierApp(
        config,
        template_path=template_path,
        mailer=mailer,
        idp=idp,
    )

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

        config.filters.append(filter)

    app.process_leases()
