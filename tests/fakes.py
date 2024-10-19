import datetime

from email.mime.multipart import MIMEMultipart

from esi_lease_notifier.models import User
from esi_lease_notifier.models import Project
from esi_lease_notifier.models import Lease
from esi_lease_notifier.models import RoleAssignment
from esi_lease_notifier.models import IdReference
from esi_lease_notifier.models import Scope


class FakeMailer:
    record: list[MIMEMultipart]

    def __init__(self):
        self.record = []

    def send_message(self, msg: MIMEMultipart) -> None:
        self.record.append(msg)


class FakeIdp:
    def get_users(self) -> list[User]:
        return [
            User(id="1", name="alice", email="alice@example.com"),
            User(id="2", name="bob", email="bob@example.com"),
            User(id="3", name="carol"),
        ]

    def get_projects(self) -> list[Project]:
        return [
            Project(id="1", name="project1"),
            Project(id="2", name="project2"),
        ]

    def get_leases(self) -> list[Lease]:
        return [
            Lease(
                id="1",
                resource_name="test_resource",
                project_id="1",
                start_time=datetime.datetime.now(),
                end_time=datetime.datetime.now() + datetime.timedelta(days=8),
            ),
            Lease(
                id="2",
                resource_name="test_resource",
                project_id="2",
                start_time=datetime.datetime.now(),
                end_time=datetime.datetime.now() + datetime.timedelta(days=2),
            ),
        ]

    def get_role_assignments(self) -> list[RoleAssignment]:
        return [
            RoleAssignment(
                role=IdReference(id="1"),
                scope=Scope(project=IdReference(id="1")),
                user=IdReference(id="1"),
            ),
            RoleAssignment(
                role=IdReference(id="1"),
                scope=Scope(project=IdReference(id="1")),
                user=IdReference(id="2"),
            ),
            RoleAssignment(
                role=IdReference(id="1"),
                scope=Scope(project=IdReference(id="2")),
                user=IdReference(id="2"),
            ),
            RoleAssignment(
                role=IdReference(id="1"),
                scope=Scope(project=IdReference(id="2")),
                user=IdReference(id="3"),
            ),
        ]
