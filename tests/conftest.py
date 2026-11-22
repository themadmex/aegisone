import pytest
from django.db import transaction
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.models import User
from apps.core import tenancy
from apps.workspaces import services
from apps.workspaces.models import Membership


@pytest.fixture(autouse=True)
def _fast_hashing(settings):
    settings.RATELIMIT_ENABLE = False


def make_user(email, name="", password="correct horse battery staple"):
    return User.objects.create_user(email=email, password=password, name=name)


def add_member(workspace, user, role):
    with transaction.atomic():
        tenancy.set_workspace(workspace.id)
        return Membership.objects.create(workspace=workspace, user=user, role=role)


@pytest.fixture
def workspace_factory(transactional_db):
    def factory(name, owner_email, owner_name="Owner"):
        workspace, _ = services.provision_workspace(name, owner_email)
        owner = make_user(owner_email, owner_name)
        add_member(workspace, owner, Membership.OWNER)
        return workspace, owner

    return factory


def sign_in_verified(client, user):
    """Sign in and mark the session as MFA-verified, as the real flow does."""
    device = TOTPDevice.objects.filter(user=user, confirmed=True).first() or TOTPDevice.objects.create(
        user=user, name="test", confirmed=True
    )
    client.force_login(user)
    session = client.session
    session["otp_device_id"] = device.persistent_id
    session.save()
    return client
