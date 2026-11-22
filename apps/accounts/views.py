from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST
from django_ratelimit.decorators import ratelimit

from apps.core import audit, tokens
from apps.workspaces import services as workspace_services

from . import mfa
from .forms import AcceptInviteForm, CodeForm, RecoveryRequestForm, SetPasswordForm, SignInForm
from .models import AccountToken, User, normalize_email

SESSION_NEXT = "aegis_next"
GENERIC_SIGN_IN_ERROR = "That email and password don’t match. Check both and try again, or reset your password."


def _safe_next(request, candidate):
    if candidate and url_has_allowed_host_and_scheme(candidate, {request.get_host()}, request.is_secure()):
        return candidate
    return reverse("workspaces:overview")


@require_http_methods(["GET", "POST"])
@ratelimit(key="ip", rate="20/15m", method="POST", block=True)
@ratelimit(key="post:email", rate="10/15m", method="POST", block=True)
def sign_in(request):
    if request.user.is_authenticated and request.user.is_verified():
        return redirect("workspaces:overview")
    form = SignInForm(request.POST or None)
    error = None
    if request.method == "POST":
        if form.is_valid():
            user = authenticate(request, email=form.cleaned_data["email"], password=form.cleaned_data["password"])
            if user is not None:
                login(request, user)
                request.session[SESSION_NEXT] = _safe_next(request, request.GET.get("next"))
                audit.record("auth.password_ok", actor=user)
                return redirect("accounts:mfa")
            audit.record("auth.password_failed", outcome="failure")
        error = GENERIC_SIGN_IN_ERROR
    return render(
        request,
        "accounts/sign_in.html",
        {"form": form, "error": error, "ended": request.GET.get("ended") == "1"},
        status=400 if error else 200,
    )


@require_POST
def sign_out(request):
    logout(request)
    return redirect("accounts:sign_in")


@require_http_methods(["GET", "POST"])
@ratelimit(key="user_or_ip", rate="10/15m", method="POST", block=True)
def mfa_step(request):
    """Second factor: enrol an authenticator if the user has none, otherwise verify."""
    user = request.user
    if not user.is_authenticated:
        return redirect("accounts:sign_in")
    if user.is_verified():
        return redirect(request.session.pop(SESSION_NEXT, None) or "workspaces:overview")

    form = CodeForm(request.POST or None)
    error = None
    if mfa.confirmed_totp(user) is None:
        device = mfa.pending_totp(user)
        if request.method == "POST" and form.is_valid():
            if device.verify_token(form.cleaned_data["code"]):
                device.confirmed = True
                device.save(update_fields=["confirmed"])
                codes = mfa.issue_recovery_codes(user)
                _login_device(request, device)
                audit.record("mfa.enrolled", actor=user)
                return render(request, "accounts/recovery_codes.html", {"codes": codes, "next": request.session.pop(SESSION_NEXT, None)})
            error = "That code didn’t work. Codes change every 30 seconds, so use the newest one."
        key, svg = mfa.setup_material(device)
        return render(
            request, "accounts/mfa_setup.html", {"form": form, "error": error, "key": key, "qr_svg": svg},
            status=400 if error else 200,
        )

    if request.method == "POST" and form.is_valid():
        method = mfa.verify(request, user, form.cleaned_data["code"])
        if method:
            audit.record("mfa.verified", actor=user, target=method)
            return redirect(request.session.pop(SESSION_NEXT, None) or "workspaces:overview")
        audit.record("mfa.failed", actor=user, outcome="failure")
        error = "That code didn’t work. Codes change every 30 seconds, so use the newest one."
    return render(request, "accounts/mfa_verify.html", {"form": form, "error": error}, status=400 if error else 200)


def _login_device(request, device):
    from django_otp import login as otp_login

    otp_login(request, device)
    return True


@require_http_methods(["GET", "POST"])
@ratelimit(key="ip", rate="10/h", method="POST", block=True)
@ratelimit(key="post:email", rate="3/h", method="POST", block=True)
def recovery_request(request):
    form = RecoveryRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = User.objects.filter(email=form.cleaned_data["email"], is_active=True).first()
        if user is not None:
            raw, digest = tokens.new_token()
            AccountToken.objects.create(
                user=user, purpose=AccountToken.PURPOSE_RECOVERY, digest=digest,
                expires_at=timezone.now() + settings.RECOVERY_LIFETIME,
            )
            minutes = int(settings.RECOVERY_LIFETIME.total_seconds() // 60)
            send_mail(
                subject="Reset your AegisOne Open password",
                message=(
                    f"Use this link to choose a new password: {settings.APP_BASE_URL}/recovery/{raw}\n\n"
                    f"It works once and expires in {minutes} minutes. If you didn't ask for this, ignore this email."
                ),
                from_email=None, recipient_list=[user.email],
            )
            audit.record("recovery.requested", actor=user)
        # Identical response whether or not the account exists.
        return render(request, "accounts/recovery_sent.html")
    return render(request, "accounts/recovery_request.html", {"form": form})


@require_http_methods(["GET", "POST"])
@ratelimit(key="ip", rate="20/h", method="POST", block=True)
def recovery_confirm(request, token):
    digest = tokens.digest(token)
    record = AccountToken.objects.select_related("user").filter(
        digest=digest, purpose=AccountToken.PURPOSE_RECOVERY
    ).first()
    now = timezone.now()
    if record is None or record.consumed_at or record.expires_at <= now or not record.user.is_active:
        return render(request, "accounts/link_unavailable.html", {"kind": "reset"}, status=410)

    form = SetPasswordForm(request.POST or None, user=record.user)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            consumed = AccountToken.objects.filter(pk=record.pk, consumed_at__isnull=True).update(consumed_at=now)
            if consumed != 1:
                return render(request, "accounts/link_unavailable.html", {"kind": "reset"}, status=410)
            user = record.user
            user.set_password(form.cleaned_data["password"])
            user.save(update_fields=["password"])
            user.end_all_sessions()
            audit.record("recovery.completed", actor=user)
        logout(request)
        return redirect(f"{reverse('accounts:sign_in')}?reset=1")
    return render(request, "accounts/recovery_confirm.html", {"form": form})


@require_http_methods(["GET", "POST"])
@ratelimit(key="ip", rate="30/h", method="POST", block=True)
def accept_invite(request, token):
    invitation = workspace_services.find_invitation(token)
    now = timezone.now()
    if invitation is None or not invitation.is_pending(now):
        return render(request, "accounts/link_unavailable.html", {"kind": "invite"}, status=410)

    user = request.user if request.user.is_authenticated else None
    if user is not None and normalize_email(user.email) != invitation.email:
        return render(
            request, "accounts/invite_wrong_account.html",
            {"invitation": invitation, "signed_in_as": user.email}, status=409,
        )

    existing = User.objects.filter(email=invitation.email).first()
    if user is None and existing is not None:
        # Existing account: sign in first, then come back to accept.
        return redirect(f"{reverse('accounts:sign_in')}?next={request.path}")

    if user is not None:
        if request.method == "POST":
            try:
                workspace_services.accept(invitation, user)
            except workspace_services.InvitationUnavailable:
                return render(request, "accounts/link_unavailable.html", {"kind": "invite"}, status=410)
            return redirect("workspaces:overview")
        return render(request, "accounts/invite_join.html", {"invitation": invitation})

    form = AcceptInviteForm(request.POST or None, user=User(email=invitation.email))
    if request.method == "POST" and form.is_valid():
        new_user = User.objects.create_user(
            email=invitation.email, password=form.cleaned_data["password"], name=form.cleaned_data["name"]
        )
        try:
            workspace_services.accept(invitation, new_user)
        except workspace_services.InvitationUnavailable:
            transaction.set_rollback(True)
            return render(request, "accounts/link_unavailable.html", {"kind": "invite"}, status=410)
        login(request, new_user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("accounts:mfa")
    return render(request, "accounts/invite_accept.html", {"invitation": invitation, "form": form})
