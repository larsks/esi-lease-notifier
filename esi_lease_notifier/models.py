from typing import Self, Literal, Annotated, override

import datetime

from enum import StrEnum
from enum import IntEnum
from esi.lease.v1.lease import Lease
from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator
from pydantic import BeforeValidator
from pydantic import ConfigDict


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


class Filter(BaseModel):
    def selects(self, lease: Lease) -> bool:
        return False


class ExpirationFilter(Filter):
    kind: Literal["expiration"] = "expiration"
    days_until_expiration: int

    @override
    def selects(self, lease: Lease) -> bool:
        return datetime.datetime.fromisoformat(
            lease.end_time
        ) < datetime.datetime.now() + datetime.timedelta(
            days=self.days_until_expiration
        )


class ProjectFilter(Filter):
    kind: Literal["project"] = "project"
    project_id: str

    @override
    def selects(self, lease: Lease) -> bool:
        return lease.project_id == self.project_id or lease.project == self.project_id


class LeaseNotifierConfiguration(BaseModel):
    email: EmailConfiguration
    openstack: OpenstackConfiguration
    filters: list[Filter] = []
    template_path: str | None = None


class ConfigurationFile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    esi_lease_notifier: LeaseNotifierConfiguration = Field(
        ..., alias="esi-lease-notifier"
    )


def maybeDateTime(v: str | datetime.datetime):
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
    resource_name: str
    resource_uuid: str
    resource_class: str
    owner: str
    owner_id: str
    project: str
    project_id: str
    start_time: isoDateTime
    end_time: isoDateTime
    expire_time: isoDateTime | None = None
    status: LeaseStatus
    id: str


class idReference(BaseModel):
    id: str


class Scope(BaseModel):
    project: idReference | None = None


class RoleAssignment(BaseModel):
    role: idReference
    scope: Scope
    user: idReference
