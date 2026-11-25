"""Workspace, membership and invitation rules.

All functions run inside the request transaction. Callers must already have
set tenant context for the workspace they act on; functions that start from an
untrusted token set the narrow context themselves.
"""

import uuid

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import normalize_email
from apps.core import audit, tenancy, tokens

from .models import Invitation, Membership, Workspace


class InvitationUnavailable(Exception):
    """Expired, already used, replaced or unknown. Callers show one generic state."""


class LastOwnerError(Exception):
    pass


class AlreadyMemberError(Exception):
    pass


def provision_workspace(name, owner_email):
    """Operator provisioning for the invite-only pilot. Returns (workspace, raw_owner_token)."""
    with transaction.atomic():
        workspace_id = uuid.uuid4()
        tenancy.set_workspace(workspace_id)
        workspace = Workspace.objects.create(id=workspace_id, name=name.strip())
        raw = _issue_invitation(workspace, owner_email, Membership.OWNER, invited_by=None)
        audit.record("workspace.provisioned", workspace=workspace, target=workspace.id)
    return workspace, raw


def invite(workspace, email, role, invited_by):
    """Owner invites someone. Replaces any pending invite for the same email."""
    email = normalize_email(email)
    active = Membership.objects.filter(
        workspace=workspace, user__email=email, revoked_at__isnull=True
    ).exists()
    if active:
        raise AlreadyMemberError
    raw = _issue_invitation(workspace, email, role, invited_by)
    audit.record("invitation.created", actor=invited_by, workspace=workspace)
    return raw


def resend(workspace, invitation_id, actor):
    old = Invitation.objects.get(workspace=workspace, id=invitation_id)
    if old.consumed_at is not None:
        raise InvitationUnavailable
    raw = _issue_invitation(workspace, old.email, old.role, actor)
    audit.record("invitation.resent", actor=actor, workspace=workspace)
    return old.email, raw


def cancel(workspace, invitation_id, actor):
    updated = Invitation.objects.filter(
        workspace=workspace, id=invitation_id, consumed_at__isnull=True, retired_at__isnull=True
    ).update(retired_at=timezone.now())
    if updated:
        audit.record("invitation.cancelled", actor=actor, workspace=workspace)
    return bool(updated)


def _issue_invitation(workspace, email, role, invited_by):
    email = normalize_email(email)
    now = timezone.now()
    Invitation.objects.filter(
        workspace=workspace, email=email, consumed_at__isnull=True, retired_at__isnull=True
    ).update(retired_at=now)
    raw, digest = tokens.new_token()
    Invitation.objects.create(
        workspace=workspace,
        email=email,
        role=role,
        token_digest=digest,
        invited_by=invited_by,
        expires_at=now + settings.INVITATION_LIFETIME,
    )
    _send_invitation_email(email, raw, workspace, invited_by)
    return raw


def _send_invitation_email(email, raw, workspace, invited_by):
    link = f"{settings.APP_BASE_URL}/invite/{raw}"
    inviter = invited_by.display_name if invited_by else "The AegisOne Open team"
    hours = int(settings.INVITATION_LIFETIME.total_seconds() // 3600)
    send_mail(
        subject=f"You're invited to {workspace.name} on AegisOne Open",
        message=(
            f"{inviter} invited you to join {workspace.name} on AegisOne Open.\n\n"
            f"Open this link to set up your account: {link}\n\n"
            f"The link works once and expires in {hours} hours. "
            "If you weren't expecting this, you can ignore this email."
        ),
        from_email=None,
        recipient_list=[email],
    )


def find_invitation(raw):
    """Look up an invitation from an untrusted token. Only that one row becomes visible."""
    digest = tokens.digest(raw)
    tenancy.set_invite_digest(digest)
    return Invitation.objects.select_related("workspace").filter(token_digest=digest).first()


def accept(invitation, user):
    """Consume the invitation once and grant membership. Safe under concurrent redemption."""
    if normalize_email(user.email) != invitation.email:
        raise InvitationUnavailable
    tenancy.set_workspace(invitation.workspace_id)
    workspace = Workspace.objects.select_for_update().get(pk=invitation.workspace_id)
    if workspace.status != Workspace.ACTIVE:
        raise InvitationUnavailable
    now = timezone.now()
    consumed = Invitation.objects.filter(
        pk=invitation.pk, consumed_at__isnull=True, retired_at__isnull=True, expires_at__gt=now
    ).update(consumed_at=now)
    if consumed != 1:
        raise InvitationUnavailable
    membership, created = Membership.objects.get_or_create(
        workspace_id=invitation.workspace_id, user=user, defaults={"role": invitation.role}
    )
    if not created:
        membership.role = invitation.role
        membership.revoked_at = None
        membership.save(update_fields=["role", "revoked_at"])
    audit.record("invitation.accepted", actor=user, workspace=invitation.workspace, target=membership.id)
    return membership


def remove_member(workspace, membership_id, actor):
    """Revoke a membership. A workspace always keeps at least one active owner."""
    Workspace.objects.select_for_update().get(pk=workspace.pk)  # serialise owner changes
    membership = Membership.objects.get(workspace=workspace, id=membership_id, revoked_at__isnull=True)
    if membership.is_owner:
        owners = Membership.objects.filter(workspace=workspace, role=Membership.OWNER, revoked_at__isnull=True)
        if owners.count() <= 1:
            raise LastOwnerError
    membership.revoked_at = timezone.now()
    membership.save(update_fields=["revoked_at"])
    audit.record("membership.removed", actor=actor, workspace=workspace, target=membership.id)
    return membership


def active_memberships(user):
    """Memberships visible through the current-user policy, for the switcher."""
    return list(
        Membership.objects.select_related("workspace")
        .filter(user=user, revoked_at__isnull=True, workspace__status=Workspace.ACTIVE)
        .order_by("workspace__name")
    )
