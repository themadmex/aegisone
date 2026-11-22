"""Test settings: run as the schema owner so pytest can create the test database.

The owner role is not a superuser and has no BYPASSRLS, and every tenant table
uses FORCE ROW LEVEL SECURITY, so application code under test is still bound by
the same policies as the runtime role. Tests that must prove the runtime role's
grants connect as that role explicitly.
"""

import os

os.environ.setdefault("DJANGO_DEBUG", "1")
os.environ["DJANGO_DB_ROLE"] = "owner"

from .settings import *  # noqa: E402,F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
RATELIMIT_ENABLE = True
DATABASES["default"]["CONN_MAX_AGE"] = 0  # noqa: F405
