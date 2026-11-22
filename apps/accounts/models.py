import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower


def normalize_email(email):
    return (email or "").strip().lower()


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, email):
        return self.get(email=normalize_email(email))

    def create_user(self, email, password=None, name=""):
        user = self.model(email=normalize_email(email), name=name.strip())
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, *args, **kwargs):
        raise NotImplementedError("There are no superusers. Operators use audited, separate tooling.")


class User(AbstractBaseUser):
    """Global identity. Workspace access comes only from active memberships."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Unique and forced to lower case, so uniqueness is case-insensitive.
    email = models.EmailField(max_length=254, unique=True)
    name = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    # Bumped to end every existing session (password reset, disable).
    session_generation = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "users"
        constraints = [
            models.CheckConstraint(condition=models.Q(email=Lower("email")), name="users_email_lowercase"),
        ]

    def save(self, *args, **kwargs):
        self.email = normalize_email(self.email)
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.name or self.email

    @property
    def initials(self):
        parts = [p for p in self.display_name.replace("@", " ").split() if p]
        return "".join(p[0] for p in parts[:2]).upper() or "?"

    def end_all_sessions(self):
        self.session_generation = models.F("session_generation") + 1
        self.save(update_fields=["session_generation"])
        self.refresh_from_db(fields=["session_generation"])


class AccountToken(models.Model):
    """Single-use, expiring account link. Only a SHA-256 digest is stored."""

    PURPOSE_RECOVERY = "recovery"
    PURPOSES = [(PURPOSE_RECOVERY, "Password recovery")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="account_tokens")
    purpose = models.CharField(max_length=16, choices=PURPOSES)
    digest = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "account_tokens"
        constraints = [
            models.CheckConstraint(condition=models.Q(purpose__in=["recovery"]), name="account_token_purpose_valid")
        ]
