from datetime import timedelta
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.core import audit, tenancy
from apps.posture.models import DomainJob, ExportPayload, Report
from apps.posture.services import lock_workspace
from apps.workspaces.models import Workspace


class Command(BaseCommand):
    help = "Preview or apply retention of expired exports, old DNS observations and revoked reports."

    def add_arguments(self, parser):
        parser.add_argument("--workspace", required=True, type=UUID)
        parser.add_argument("--apply", action="store_true", help="Apply deletion to the listed expired artifacts.")

    @transaction.atomic
    def handle(self, *args, workspace, apply, **options):
        tenancy.set_workspace(workspace)
        try:
            record = Workspace.objects.get(pk=workspace)
        except Workspace.DoesNotExist as error:
            raise CommandError("Workspace not found.") from error
        lock_workspace(record, allow_closed=True)
        now = timezone.now()
        scopes = {
            "expired exports": ExportPayload.objects.filter(workspace=record, expires_at__lte=now),
            "old DNS observations": DomainJob.objects.filter(
                workspace=record, finished_at__lte=now - timedelta(days=90),
            ).exclude(observations=[]),
            "revoked reports": Report.objects.filter(workspace=record, revoked_at__lte=now - timedelta(days=30)),
        }
        counts = {scope: rows.count() for scope, rows in scopes.items()}
        if apply:
            scopes["expired exports"].delete()
            scopes["old DNS observations"].update(observations=[])
            scopes["revoked reports"].delete()
            audit.record("workspace.retention_applied", workspace=record, target=record.pk)
        mode = "Applied" if apply else "Preview"
        summary = ", ".join(f"{count} {scope}" for scope, count in counts.items())
        self.stdout.write(f"{mode}: {summary}")
