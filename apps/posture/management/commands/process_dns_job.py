from uuid import UUID

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.posture.domains import run_pending


class Command(BaseCommand):
    help = "Process one pending public DNS request for an explicitly configured workspace."

    def add_arguments(self, parser):
        parser.add_argument("--workspace", required=True, type=UUID)

    def handle(self, *args, workspace, **options):
        if not settings.DNS_CHECKS_ENABLED:
            raise CommandError("DNS checks are disabled.")
        if run_pending(workspace):
            self.stdout.write("DNS job processed.")
        else:
            self.stdout.write("No eligible DNS job.")
