from typing import Self, Literal, Annotated, Protocol, override

import datetime

from pathlib import Path
from enum import StrEnum
from enum import IntEnum
from pydantic import BaseModel, field_validator
from pydantic import Field
from pydantic import model_validator
from pydantic import BeforeValidator
from pydantic import ConfigDict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def maybeDateTime(v: str | datetime.datetime) -> datetime.datetime:
    if isinstance(v, str):
        return datetime.datetime.fromisoformat(v)
    elif isinstance(v, datetime.datetime):
        return v
    else:
        raise ValueError("must be a string or datetime object")


isoDateTime = Annotated[datetime.datetime, BeforeValidator(maybeDateTime)]


class LeaseStatus(StrEnum):
    ACTIVE = "active"


class User(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: str | None = None
    id: str
    name: str
    description: str | None = None
    is_enabled: bool = True


class Project(BaseModel):
    id: str
    name: str
    is_domain: bool = False
    is_enabled: bool = True


class Lease(BaseModel):
    id: str
    resource_name: str
    project_id: str
    start_time: isoDateTime
    end_time: isoDateTime
    expire_time: isoDateTime | None = None
    status: LeaseStatus = LeaseStatus.ACTIVE


class IdReference(BaseModel):
    id: str


class Scope(BaseModel):
    project: IdReference | None = None


class RoleAssignment(BaseModel):
    role: IdReference
    scope: Scope
    user: IdReference


class EmailTLSOption(IntEnum):
    EMAIL_TLS_NONE = 0
    EMAIL_TLS_SSL = 1
    EMAIL_TLS_STARTTLS = 2


class EmailConfiguration(BaseModel):
    smtp_server: str = "127.0.0.1"
    smtp_port: int = 25
    smtp_tls: EmailTLSOption = EmailTLSOption.EMAIL_TLS_NONE
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str

    @field_validator("smtp_server")
    @classmethod
    def validate_smtp_server(cls, val: str) -> str:
        # when using a unix socket with python's smtplib we need
        # to provide an absolute path, but we want to be able to
        # use relative paths in our config. Look for servers
        # specified as `unix:<path>`, extract that path, and
        # then compute the absolute path.
        if val.startswith("unix:"):
            relpath = val[5:]
            val = str(Path(relpath).absolute())

        return val

    @model_validator(mode="after")
    def set_smtp_tls(self) -> Self:
        if self.smtp_tls is None:
            if self.smtp_port == 465:
                self.smtp_tls = EmailTLSOption.EMAIL_TLS_SSL
            elif self.smtp_port == 587:
                self.smtp_tls = EmailTLSOption.EMAIL_TLS_STARTTLS

        return self


class OpenstackConfiguration(BaseModel):
    cloud: str | None = None


class ProjectResolver(Protocol):
    def resolve_project(self, name_or_id: str) -> Project: ...


class Filter(BaseModel):
    def selects(self, lease: Lease) -> bool:  # pyright: ignore[reportUnusedParameter]
        return False

    def resolve(self, resolver: ProjectResolver) -> None:  # pyright: ignore[reportUnusedParameter]
        pass


class ExpiresFilter(Filter):
    kind: Literal["expires"] = "expires"
    daysleft: int

    @override
    def selects(self, lease: Lease) -> bool:
        return lease.end_time <= datetime.datetime.now() + datetime.timedelta(
            days=self.daysleft
        )


class ProjectFilter(Filter):
    kind: Literal["project"] = "project"
    project: str
    _project: Project

    @override
    def selects(self, lease: Lease) -> bool:
        return lease.project_id == self._project.id

    @override
    def resolve(self, resolver: ProjectResolver):
        self._project = resolver.resolve_project(self.project)


class LeaseNotifierConfiguration(BaseModel):
    email: EmailConfiguration
    openstack: OpenstackConfiguration | None = None
    filters: list[ProjectFilter | ExpiresFilter] = []
    template_path: str | None = None


class ConfigurationFile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    esi_lease_notifier: LeaseNotifierConfiguration = Field(
        ..., alias="esi-lease-notifier"
    )


class Message(BaseModel):
    msg_from: str
    recipients: list[str]
    subject: str
    body_html: str
    body_text: str

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("messages must have at least one recipient")

        return v

    def as_mime_multipart(self) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(self.body_text, "plain"))
        msg.attach(MIMEText(self.body_html, "html"))
        msg["From"] = self.msg_from
        msg["To"] = self.msg_to
        msg["Subject"] = self.subject

        return msg

    @property
    def msg_to(self) -> str:
        return ",".join(self.recipients)
