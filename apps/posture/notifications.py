import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

logger = logging.getLogger(__name__)


def notify_data_request(email, kind, status, *, link_available=True):
    link = f"\n\nView your workspace requests: {settings.APP_BASE_URL}/settings/data" if link_available else ""
    message = f"Your AegisOne request for {kind.lower()} is now {status.lower()}.{link}"

    def send():
        try:
            send_mail("AegisOne workspace request update", message, None, [email])
        except OSError:
            logger.warning("Workspace request email could not be delivered")

    transaction.on_commit(send)
