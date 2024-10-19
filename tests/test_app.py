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

from tests.fakes import FakeIdp
from tests.fakes import FakeMailer


@pytest.fixture
def idp():
    return FakeIdp()


@pytest.fixture
def config():
    return LeaseNotifierConfiguration(
        openstack=OpenstackConfiguration(),
        email=EmailConfiguration(smtp_from="test@example.com"),
    )


@pytest.fixture
def mailer():
    return FakeMailer()


@pytest.fixture
def app(
    templates: str,
    config: LeaseNotifierConfiguration,
    idp: IdpProtocol,
    mailer: MailerProtocol,
):
    return NotifierApp(config, template_path=templates, idp=idp, mailer=mailer)


def test_app(app: NotifierApp, mailer: MailerProtocol):
    app.process_leases()

    assert len(mailer.record) == 2
    assert set(mailer.record[0]["to"].split(",")) == {
        "alice@example.com",
        "bob@example.com",
    }
    assert mailer.record[1]["to"] == "bob@example.com"


def test_project_filter_by_id(app: NotifierApp, mailer: MailerProtocol):
    app.config.filters.append(ProjectFilter(project="1"))  # pyright: ignore[reportCallIssue]
    app.process_leases()

    assert len(mailer.record) == 1
    assert set(mailer.record[0]["to"].split(",")) == {
        "alice@example.com",
        "bob@example.com",
    }


def test_project_filter_by_name(app: NotifierApp, mailer: MailerProtocol):
    app.config.filters.append(ProjectFilter(project="project1"))  # pyright: ignore[reportCallIssue]
    app.process_leases()

    assert len(mailer.record) == 1
    assert set(mailer.record[0]["to"].split(",")) == {
        "alice@example.com",
        "bob@example.com",
    }


def test_expires_filter(app: NotifierApp, mailer: MailerProtocol):
    app.config.filters.append(ExpiresFilter(daysleft=4))
    app.process_leases()

    assert len(mailer.record) == 1
    assert mailer.record[0]["to"] == "bob@example.com"
