from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"

    def ready(self):
        # Connects the user_logged_in receiver that stamps session policy data.
        from . import middleware  # noqa: F401
