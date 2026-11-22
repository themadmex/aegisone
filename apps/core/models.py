import uuid

from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """Append-only security and lifecycle record.

    The runtime role is granted SELECT and INSERT only. Events never hold form
    bodies, secrets, tokens or answers: just who, what, outcome and an opaque
    reference.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    action = models.CharField(max_length=64)
    outcome = models.CharField(max_length=16, default="success")
    target_ref = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_events"
        indexes = [models.Index(fields=["workspace", "created_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(outcome__in=["success", "failure", "denied"]), name="audit_outcome_valid"
            )
        ]
