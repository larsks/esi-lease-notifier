import logging

from functools import cache, cached_property
from itertools import groupby
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .idp import IdpProtocol
from .idp import OpenstackIdp
from .mailer import MailerProtocol
from .mailer import SmtpMailer
from .models import LeaseNotifierConfiguration
from .models import Project
from .models import User
from .models import Lease
from .templates import create_template_environment

LOG = logging.getLogger(__name__)


class NotifierApp:
    def __init__(
        self,
        config: LeaseNotifierConfiguration,
        template_path: str | Path | None = None,
        idp: IdpProtocol | None = None,
        mailer: MailerProtocol | None = None,
    ):
        self.idp = idp if idp else OpenstackIdp(config.openstack)
        self.mailer = mailer if mailer else SmtpMailer(config.email)
        self.config = config
        self.env = create_template_environment(
            template_path
            if template_path
            else (config.template_path if config.template_path else "templates")
        )

    @cached_property
    def projects_by_name(self) -> dict[str, Project]:
        return {project.name: project for project in self.idp.get_projects()}

    @cached_property
    def projects_by_id(self) -> dict[str, Project]:
        return {project.id: project for project in self.idp.get_projects()}

    @cached_property
    def users_by_name(self) -> dict[str, User]:
        return {user.name: user for user in self.idp.get_users()}

    @cached_property
    def users_by_id(self) -> dict[str, User]:
        return {user.id: user for user in self.idp.get_users()}

    def get_filtered_leases(self) -> list[Lease]:
        return [
            lease
            for lease in self.idp.get_leases()
            if (not self.config.filters)
            or any(filter.selects(lease) for filter in self.config.filters)
        ]

    @cached_property
    def leases_by_project(self) -> dict[str, list[Lease]]:
        return {
            group[0]: list(group[1])
            for group in groupby(
                sorted(self.get_filtered_leases(), key=lambda lease: lease.project_id),
                key=lambda lease: lease.project_id,
            )
        }

    @cached_property
    def users_by_project(self) -> dict[str, list[User]]:
        return {
            project: set(
                self.users_by_id[assignment.user.id] for assignment in assignments
            )
            for project, assignments in groupby(
                sorted(
                    [ra for ra in self.idp.get_role_assignments() if ra.scope.project],
                    key=lambda ra: ra.scope.project.id,
                ),
                key=lambda ra: ra.scope.project.id,
            )
        }

    @cache
    def get_project_emails(self, name_or_id: str) -> list[str]:
        project = self.resolve_project(name_or_id)
        return [user.email for user in self.users_by_project[project.id] if user.email]

    @cache
    def resolve_project(self, id_or_name: str) -> Project:
        project = self.projects_by_name.get(
            id_or_name, self.projects_by_id.get(id_or_name)
        )

        if project is None:
            raise KeyError(id_or_name)

        return project

    def process_leases(self):
        subject_template = self.env.get_template("subject.txt")
        body_template_html = self.env.get_template("body.html")
        body_template_text = self.env.get_template("body.txt")

        for project_id, leases in self.leases_by_project.items():
            if not leases:
                continue

            project = self.projects_by_id[project_id]
            recipients = self.get_project_emails(project.id)
            leasetable = [
                (
                    lease.resource_name,
                    lease.start_time.isoformat(timespec="minutes"),
                    lease.end_time.isoformat(timespec="minutes"),
                )
                for lease in leases
            ]
            LOG.info(
                "send email to %s in project %s", ",".join(recipients), project.name
            )

            subject = subject_template.render(project=project, leases=leasetable)
            body_html = body_template_html.render(project=project, leases=leasetable)
            body_text = body_template_text.render(project=project, leases=leasetable)

            self.mailer.send_message(
                self.build_message(
                    self.config.email.smtp_from,
                    recipients,
                    subject,
                    body_html,
                    body_text,
                )
            )

    def build_message(
        self, msg_from, msg_recipients, msg_subject, body_html, body_text
    ):
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))
        msg["From"] = msg_from
        msg["To"] = ",".join(msg_recipients)
        msg["Subject"] = msg_subject

        return msg
