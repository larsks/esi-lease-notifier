import logging

from functools import cache, cached_property
from itertools import groupby
from pathlib import Path

from .idp import IdpProtocol
from .idp import OpenstackIdp
from .mailer import MailerProtocol
from .mailer import SmtpMailer
from .models import LeaseNotifierConfiguration
from .models import Project
from .models import User
from .models import Lease
from .models import Message
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
        if idp:
            self.idp = idp
        elif config.openstack:
            self.idp = OpenstackIdp(cloud=config.openstack.cloud)
        else:
            self.idp = OpenstackIdp()

        self.mailer = (
            mailer
            if mailer
            else SmtpMailer(
                smtp_from=config.email.smtp_from,
                smtp_server=config.email.smtp_server,
                smtp_port=config.email.smtp_port,
                smtp_tls=config.email.smtp_tls,
                smtp_username=config.email.smtp_username,
                smtp_password=config.email.smtp_password,
            )
        )
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
    def users_by_project(self) -> dict[str, set[User]]:
        return {
            project: set(
                self.users_by_id[assignment.user.id] for assignment in assignments
            )
            for project, assignments in groupby(
                sorted(
                    [ra for ra in self.idp.get_role_assignments() if ra.scope.project],
                    key=lambda ra: ra.scope.project.id,  # pyright: ignore[reportOptionalMemberAccess]
                ),
                key=lambda ra: ra.scope.project.id,  # pyright: ignore[reportOptionalMemberAccess]
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

        self.resolve_filters()

        for project_id, leases in self.leases_by_project.items():
            project = self.projects_by_id[project_id]
            recipients = self.get_project_emails(project.id)

            if not leases:
                LOG.info("no leases for project %s", project.name)
                continue

            if not recipients:
                LOG.warning(
                    "%d leases for project %s but no recipients",
                    len(leases),
                    project.name,
                )
                continue

            leasetable = [
                (
                    lease.resource_name,
                    lease.start_time.isoformat(timespec="minutes"),
                    lease.end_time.isoformat(timespec="minutes"),
                )
                for lease in leases
            ]
            LOG.info(
                "message to %s for project %s with %d leases",
                ",".join(recipients),
                project.name,
                len(leases),
            )

            subject = subject_template.render(project=project, leases=leasetable)
            body_html = body_template_html.render(project=project, leases=leasetable)
            body_text = body_template_text.render(project=project, leases=leasetable)

            message = Message(
                msg_from=self.config.email.smtp_from,
                recipients=recipients,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
            )
            self.mailer.send_message(message.as_mime_multipart())

    def resolve_filters(self):
        """Transform project name references in filters into project ids."""
        for filter in self.config.filters:
            filter.resolve(self)
