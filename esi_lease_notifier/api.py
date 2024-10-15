import datetime
import logging

from typing import Generator

from esi.connection import ESIConnection
from esi.lease.v1.lease import Lease
from functools import cached_property, cache
from openstack.identity.v3.project import Project
from openstack.identity.v3.role_assignment import RoleAssignment
from openstack.identity.v3.user import User
from itertools import groupby

LOG = logging.getLogger(__name__)


class NotifierApi:
    def __init__(self, conn: ESIConnection):
        self.conn = conn

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

    @cache
    def _get_leases(self, filterspec: tuple[str] | None = None) -> list[Lease]:
        filter: dict[str, str] = (
            dict(x.split("=", 1) for x in filterspec) if filterspec else {}
        )
        leases = self.conn.lease.leases()
        if expiring := filter.get("expiring"):
            return [
                lease
                for lease in leases
                if datetime.datetime.strptime(lease.end_time[:19], "%Y-%m-%dT%H:%M:%S")
                < datetime.datetime.now() + datetime.timedelta(days=int(expiring))
            ]

        return list(leases)

    def get_leases(
        self, filterspec: tuple[str] | None = None
    ) -> Generator[Lease, None, None]:
        LOG.info("getting leases")
        return groupby(
            sorted(self._get_leases(filterspec), key=lambda lease: lease.project_id),
            key=lambda lease: lease.project_id,
        )
