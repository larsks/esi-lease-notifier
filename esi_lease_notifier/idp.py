from typing import Protocol

import esi

from functools import cache

from .models import OpenstackConfiguration
from .models import User
from .models import Project
from .models import Lease
from .models import RoleAssignment


class IdpProtocol(Protocol):
    def get_users(self) -> list[User]: ...
    def get_projects(self) -> list[Project]: ...
    def get_leases(self) -> list[Lease]: ...
    def get_role_assignments(self) -> list[RoleAssignment]: ...


class OpenstackIdp:
    def __init__(self, config: OpenstackConfiguration | None = None):
        self.conn = esi.connect(cloud=config.cloud if config else None)

    @cache
    def get_users(self) -> list[User]:
        return [User.model_validate(user) for user in self.conn.identity.users()]

    @cache
    def get_projects(self) -> list[Project]:
        return [
            Project.model_validate(project) for project in self.conn.identity.projects()
        ]

    @cache
    def get_role_assignments(self) -> list[RoleAssignment]:
        return [
            RoleAssignment.model_validate(ra)
            for ra in self.conn.identity.role_assignments()
        ]

    @cache
    def get_leases(self) -> list[Lease]:
        return [Lease.model_validate(lease) for lease in self.conn.lease.leases()]
