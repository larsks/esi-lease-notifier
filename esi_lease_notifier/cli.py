import click
import datetime
import esi
import io
import jinja2
import jinja2.loaders
import logging
import yaml
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from prettytable import PrettyTable
from openstack.identity.v3.project import Project

from .models import ConfigurationFile, EmailConfiguration
from .api import NotifierApi

LOG = logging.getLogger(__name__)
LOGLEVELS = ["WARNING", "INFO", "DEBUG"]
DEFAULT_CONFIG_FILE = "esi-lease-notifier.yaml"


def send_email(
    config: EmailConfiguration,
    project: Project,
    recipients: str,
    subject: str,
    text_body: str,
    html_body: str,
):
    LOG.info("sending email for project %s to %s", project.name, recipients)

    msg = MIMEMultipart("alternative")
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    msg["From"] = config.smtp_from
    msg["To"] = recipients
    msg["Subject"] = subject

    with smtplib.SMTP(config.smtp_server, config.smtp_port) as mailer:
        mailer.starttls()
        mailer.login(config.smtp_username, config.smtp_password)
        mailer.send_message(msg)


def tabulate(
    data: list[list[str]], headings: list[str] | None = None, html: bool = False
):
    table = PrettyTable()
    if headings:
        table.field_names = headings

    table.add_rows(data)

    if html:
        return table.get_html_string()
    else:
        return table


@click.command()
@click.option("--template-directory", "-d", default="templates")
@click.option(
    "--config-file", "--config", "-c", default=DEFAULT_CONFIG_FILE, type=click.File()
)
@click.option("--filter", "-f", multiple=True)
@click.option("--os-cloud")
@click.option("--verbosity", "-v", count=True)
@click.option("--recipients", "limit_recipients", multiple=True)
def main(
    template_directory: str,
    config_file: io.IOBase,
    filter: tuple[str] | None = None,
    os_cloud: str | None = None,
    verbosity: int = 0,
    limit_recipients: list[str] | None = None,
):
    logLevel = LOGLEVELS[min(verbosity, len(LOGLEVELS))]
    logging.basicConfig(level=logLevel)
    with config_file:
        config = ConfigurationFile.model_validate(yaml.safe_load(config_file))
        email_config = config.esi_lease_notifier.email

    LOG.info("connecting to openstack")
    conn = esi.connect(cloud=os_cloud)

    api = NotifierApi(conn)

    leases = api.get_leases(filterspec=filter)

    env = jinja2.Environment(loader=jinja2.loaders.FileSystemLoader(template_directory))
    env.filters["tabulate"] = tabulate
    subject_template = env.get_template("subject.txt")
    html_template = env.get_template("body.html")
    text_template = env.get_template("body.txt")

    # iterate through projects and find their leases (if any)
    for project_id, project_leases in leases:
        _project_leases = [
            (
                lease.resource,
                datetime.datetime.fromisoformat(lease.start_time).isoformat(
                    timespec="minutes"
                ),
                datetime.datetime.fromisoformat(lease.end_time).isoformat(
                    timespec="minutes"
                ),
            )
            for lease in project_leases
        ]

        if len(_project_leases) == 0:
            continue

        project = api.projects[project_id]

        subject = subject_template.render(project=project)

        html_body = html_template.render(project=project, leases=_project_leases)
        text_body = text_template.render(project=project, leases=_project_leases)

        # get users associated with project
        recipients = [
            recipient
            for recipient in api.get_project_emails(project_id)
            if not limit_recipients or recipient in limit_recipients
        ]
        if not recipients:
            LOG.warning(
                "no recpients; not sending notification for project %s", project.name
            )
            continue
        to = ",".join(recipients)
        send_email(
            email_config,
            project,
            to,
            subject,
            text_body,
            html_body,
        )
