from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from apps.workspaces import services


class Command(BaseCommand):
    help = "Operator tool: create a pilot workspace and email its owner a single-use invite."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="Workspace (business) name")
        parser.add_argument("--owner-email", required=True, help="Email address of the first owner")

    def handle(self, *args, name, owner_email, **options):
        try:
            validate_email(owner_email)
        except ValidationError as exc:
            raise CommandError("Enter a valid owner email address.") from exc
        workspace, _raw = services.provision_workspace(name, owner_email)
        # The raw token is only ever sent by email; it is not printed here.
        self.stdout.write(self.style.SUCCESS(f"Workspace {workspace.id} created. Owner invite emailed to {owner_email}."))
