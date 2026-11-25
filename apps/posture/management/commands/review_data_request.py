from uuid import UUID

from django.core.management.base import BaseCommand, CommandError

from apps.posture.models import DataRequest
from apps.posture.rights import review_request
from apps.workspaces.models import Workspace


class Command(BaseCommand):
    help = "Record an operator decision after verifying a workspace owner's identity and authority out of band."

    def add_arguments(self, parser):
        parser.add_argument("--workspace", required=True, type=UUID)
        parser.add_argument("--request", required=True, type=UUID)
        parser.add_argument("--verified-owner", required=True)
        parser.add_argument("--decision", choices=["review", "export", "closure", "decline"], required=True)

    def handle(self, *args, workspace, request, verified_owner, decision, **options):
        try:
            result = review_request(workspace, request, verified_owner, decision)
        except (DataRequest.DoesNotExist, Workspace.DoesNotExist, ValueError) as error:
            raise CommandError("No matching request with the required owner authorization.") from error
        self.stdout.write(f"Request {result.pk} updated to {result.status}.")
