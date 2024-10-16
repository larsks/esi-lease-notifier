import datetime
import esi
import logging

from typing import Protocol

from functools import cached_property, cache
from esi.lease.v1.lease import Lease
from openstack.identity.v3.project import Project
from openstack.identity.v3.role_assignment import RoleAssignment
from openstack.identity.v3.user import User
from itertools import groupby

from .models import OpenstackConfiguration

LOG = logging.getLogger(__name__)


class NotifierApiProtocol(Protocol):
    def get_project_emails(self, project_id: str) -> list[str]: ...

    @property
    def projects(self) -> dict[str, Project]: ...

    @property
    def role_assignments(self) -> list[RoleAssignment]: ...

    @property
    def users(self) -> list[User]: ...

    @property
    def leases(self) -> list[Lease]: ...


class NotifierApi:
    def __init__(self, config: OpenstackConfiguration):
        self.config = config
        self.conn = esi.connect(cloud=config.cloud)

    @cache
    def get_project_emails(self, project_id: str) -> list[str]:
        project_user_ids = [
            role["user"]["id"]
            for role in self.role_assignments
            if "project" in role["scope"]
            and role["scope"]["project"]["id"] == project_id
        ]

        return [
            user.email
            for user in self.users
            if user.id in project_user_ids and user.email
        ]

    @cached_property
    def projects(self) -> dict[str, Project]:
        LOG.info("getting projects")
        return {project.id: project for project in self.conn.identity.projects()}

    @cached_property
    def role_assignments(self) -> list[RoleAssignment]:
        LOG.info("getting role assignments")
        return list(self.conn.identity.role_assignments())

    @cached_property
    def users(self) -> list[User]:
        LOG.info("getting users")
        return list(self.conn.identity.users())

    @cached_property
    def leases(self) -> list[Lease]:
        return list(self.conn.lease.leases())
