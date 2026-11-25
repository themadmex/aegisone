import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from .catalog import CURRENT_VERSION, PRIORITIES


class TenantRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey("workspaces.Workspace", on_delete=models.CASCADE)

    class Meta:
        abstract = True


class Assessment(TenantRecord):
    template_version = models.PositiveSmallIntegerField(default=CURRENT_VERSION)
    answers = models.JSONField(default=dict)
    revision = models.PositiveIntegerField(default=0)
    score = models.PositiveSmallIntegerField(null=True)
    unsure_count = models.PositiveSmallIntegerField(null=True)
    submitted_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["workspace"], condition=Q(submitted_at__isnull=True), name="one_assessment_draft"),
            models.CheckConstraint(
                condition=(
                    Q(submitted_at__isnull=True, score__isnull=True, unsure_count__isnull=True)
                    | Q(submitted_at__isnull=False, score__isnull=False, unsure_count__isnull=False, score__lte=100)
                ),
                name="assessment_submission_fields",
            ),
        ]
        indexes = [models.Index(fields=["workspace", "-submitted_at"])]


class Action(TenantRecord):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"

    key = models.CharField(max_length=64)
    title = models.CharField(max_length=180)
    priority = models.PositiveSmallIntegerField(choices=PRIORITIES)
    reason = models.CharField(max_length=255)
    steps = models.TextField()
    confirmation = models.TextField()
    guidance_version = models.PositiveSmallIntegerField(default=CURRENT_VERSION)
    source_kind = models.CharField(max_length=24, default="assessment")
    source_id = models.UUIDField()
    observed_at = models.DateTimeField()
    current_gap = models.BooleanField(default=True)
    status = models.CharField(max_length=16, choices=Status, default=Status.OPEN)
    done_at = models.DateTimeField(null=True)
    revision = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["priority", "key"]
        constraints = [
            models.UniqueConstraint(fields=["workspace", "key"], name="unique_workspace_action"),
            models.UniqueConstraint(fields=["workspace", "id"], name="unique_workspace_action_id"),
            models.CheckConstraint(condition=Q(status__in=["open", "in_progress", "done"]), name="valid_action_status"),
            models.CheckConstraint(condition=Q(priority__in=[1, 2, 3]), name="valid_action_priority"),
        ]


class ActionEvent(TenantRecord):
    action = models.ForeignKey(Action, on_delete=models.CASCADE, related_name="history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    event = models.CharField(max_length=30)
    detail = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class Report(TenantRecord):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True)
    schema_version = models.PositiveSmallIntegerField(default=1)
    snapshot = models.JSONField()


class DataRequest(TenantRecord):
    class Kind(models.TextChoices):
        EXPORT = "export", "Workspace export"
        CLOSURE = "closure", "Workspace closure"

    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        IN_REVIEW = "in_review", "In review"
        COMPLETED = "completed", "Completed"
        DECLINED = "declined", "Declined"

    kind = models.CharField(max_length=12, choices=Kind)
    status = models.CharField(max_length=12, choices=Status, default=Status.RECEIVED)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "kind"], condition=Q(status__in=["received", "in_review"]),
                name="one_active_workspace_data_request",
            ),
            models.UniqueConstraint(fields=["workspace", "id"], name="unique_workspace_request_id"),
        ]


class ExportPayload(TenantRecord):
    request = models.OneToOneField(DataRequest, on_delete=models.CASCADE, related_name="export_payload")
    payload = models.JSONField()
    expires_at = models.DateTimeField()


class Domain(TenantRecord):
    name = models.CharField(max_length=227)
    sends_mail = models.BooleanField(default=False)
    attested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    attested_at = models.DateTimeField()
    proof_generation = models.PositiveIntegerField(default=1)
    challenge_expires_at = models.DateTimeField()
    verified_until = models.DateTimeField(null=True)
    revoked_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["workspace", "name"], name="unique_workspace_domain"),
            models.UniqueConstraint(fields=["workspace", "id"], name="unique_workspace_domain_id"),
        ]


class DomainJob(TenantRecord):
    class Kind(models.TextChoices):
        VERIFY = "verify", "Verify proof"
        CHECK = "check", "Check SPF and DMARC"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Checking"
        COMPLETE = "complete", "Complete"
        INCONCLUSIVE = "inconclusive", "Inconclusive"
        CANCELLED = "cancelled", "Cancelled"

    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name="jobs")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=8, choices=Kind)
    status = models.CharField(max_length=12, choices=Status, default=Status.QUEUED)
    proof_generation = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    lease_until = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)
    result = models.CharField(max_length=255, blank=True)
    observations = models.JSONField(default=list)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [models.UniqueConstraint(
            fields=["workspace"], condition=Q(status__in=["queued", "running"]), name="one_active_domain_job",
        )]


class DnsPermit(models.Model):
    slot = models.PositiveSmallIntegerField(primary_key=True)
    job_id = models.UUIDField(null=True)
    available_at = models.DateTimeField()


class DnsCooldown(models.Model):
    name_digest = models.CharField(primary_key=True, max_length=64)
    available_at = models.DateTimeField()
