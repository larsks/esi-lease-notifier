import pytest
import datetime

from email.mime.multipart import MIMEMultipart
from pathlib import Path

from esi_lease_notifier.app import NotifierApp
from esi_lease_notifier.idp import IdpProtocol
from esi_lease_notifier.mailer import MailerProtocol
from esi_lease_notifier.models import EmailConfiguration
from esi_lease_notifier.models import LeaseNotifierConfiguration
from esi_lease_notifier.models import OpenstackConfiguration
from esi_lease_notifier.models import User
from esi_lease_notifier.models import Project
from esi_lease_notifier.models import Lease
from esi_lease_notifier.models import RoleAssignment
from esi_lease_notifier.models import IdReference
from esi_lease_notifier.models import Scope
from esi_lease_notifier.models import ProjectFilter
from esi_lease_notifier.models import ExpiresFilter


class DummyMailer:
    record: list[MIMEMultipart]

    def __init__(self):
        self.record = []

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
                project_id="1",
                start_time=datetime.datetime.now(),
                end_time=datetime.datetime.now() + datetime.timedelta(days=8),
            ),
            Lease(
                id="2",
                resource_name="test_resource",
                resource_class="test_class",
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
def app(
    templates: str,
    config: LeaseNotifierConfiguration,
    idp: IdpProtocol,
    mailer: MailerProtocol,
):
    return NotifierApp(config, template_path=templates, idp=idp, mailer=mailer)


def test_app(app: NotifierApp, mailer: DummyMailer):
    app.process_leases()

    assert len(mailer.record) == 2
    assert set(mailer.record[0]["to"].split(",")) == {
        "alice@example.com",
        "bob@example.com",
    }
    assert mailer.record[1]["to"] == "bob@example.com"


def test_project_filter_by_id(app: NotifierApp, mailer: DummyMailer):
    app.config.filters.append(ProjectFilter(project="1"))  # pyright: ignore[reportCallIssue]
    app.process_leases()

    assert len(mailer.record) == 1
    assert set(mailer.record[0]["to"].split(",")) == {
        "alice@example.com",
        "bob@example.com",
    }


def test_project_filter_by_name(app: NotifierApp, mailer: DummyMailer):
    app.config.filters.append(ProjectFilter(project="project1"))  # pyright: ignore[reportCallIssue]
    app.process_leases()

    assert len(mailer.record) == 1
    assert set(mailer.record[0]["to"].split(",")) == {
        "alice@example.com",
        "bob@example.com",
    }


def test_expires_filter(app: NotifierApp, mailer: DummyMailer):
    app.config.filters.append(ExpiresFilter(daysleft=4))
    app.process_leases()

    assert len(mailer.record) == 1
    assert mailer.record[0]["to"] == "bob@example.com"
