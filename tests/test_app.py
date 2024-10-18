import pytest

from email.mime.multipart import MIMEMultipart

from esi_lease_notifier.app import NotifierApp
from esi_lease_notifier.models import (
    EmailConfiguration,
    LeaseNotifierConfiguration,
    OpenstackConfiguration,
    User,
)
from esi_lease_notifier.models import Project
from esi_lease_notifier.models import Lease
from esi_lease_notifier.models import RoleAssignment
from esi_lease_notifier.models import IdReference
from esi_lease_notifier.models import Scope


class DummyMailer:
    record: list[MIMEMultipart] = []

    def send_message(self, msg: MIMEMultipart) -> None:
        self.record.append(msg)


class DummyIdp:
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
                resource_class="test_class",
                project="example",
                project_id="1",
                start_time="2024-10-01T10:00",
                end_time="2024-10-30T10:00",
            ),
            Lease(
                id="2",
                resource_name="test_resource",
                resource_class="test_class",
                project="example",
                project_id="2",
                start_time="2024-10-01T10:00",
                end_time="2024-10-30T10:00",
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


@pytest.fixture
def idp():
    return DummyIdp()


@pytest.fixture
def config():
    return LeaseNotifierConfiguration(
        openstack=OpenstackConfiguration(),
        email=EmailConfiguration(smtp_from="test@example.com"),
    )


@pytest.fixture
def mailer():
    return DummyMailer()


@pytest.fixture
def app(config, idp, mailer):
    return NotifierApp(config, idp=idp, mailer=mailer)


def test_app_mailer(app, mailer):
    app.process_leases()

    assert len(mailer.record) == 2
    assert set(mailer.record[0]["to"].split(",")) == {
        "alice@example.com",
        "bob@example.com",
    }
    assert mailer.record[1]["to"] == "bob@example.com"
