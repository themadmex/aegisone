import uuid

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower


class Workspace(models.Model):
    ACTIVE, CLOSING, CLOSED = "active", "closing", "closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    timezone = models.CharField(max_length=64, default="Africa/Lagos")
    status = models.CharField(max_length=16, default=ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workspaces"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["active", "closing", "closed"]), name="workspace_status_valid"
            )
        ]

    def __str__(self):
        return self.name


class Membership(models.Model):
    OWNER, CONTRIBUTOR = "owner", "contributor"
    ROLES = [(OWNER, "Owner"), (CONTRIBUTOR, "Contributor")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=16, choices=ROLES)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "memberships"
        constraints = [
            models.UniqueConstraint(fields=["workspace", "user"], name="membership_workspace_user_unique"),
            models.CheckConstraint(condition=models.Q(role__in=["owner", "contributor"]), name="membership_role_valid"),
        ]

    @property
    def is_owner(self):
        return self.role == self.OWNER

    @property
    def is_active(self):
        return self.revoked_at is None


class Invitation(models.Model):
    """Invite bound to one exact email, role and workspace. Token stored as a digest."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField(max_length=254)
    role = models.CharField(max_length=16, choices=Membership.ROLES)
    token_digest = models.CharField(max_length=64, unique=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    # Set when a newer invite replaces this one or an owner cancels it.
    retired_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "invitations"
        constraints = [
            models.CheckConstraint(condition=models.Q(role__in=["owner", "contributor"]), name="invitation_role_valid"),
            models.CheckConstraint(condition=models.Q(email=Lower("email")), name="invitation_email_lowercase"),
        ]
        indexes = [models.Index(fields=["workspace", "email"])]

    def is_pending(self, now):
        return self.consumed_at is None and self.retired_at is None and self.expires_at > now
