from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

SESSION_AUTH_AT = "aegis_auth_at"
SESSION_GENERATION = "aegis_session_gen"

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "base-uri 'none'",
        "object-src 'none'",
    ]
)


@receiver(user_logged_in)
def _stamp_session(sender, request, user, **kwargs):
    request.session[SESSION_AUTH_AT] = timezone.now().timestamp()
    request.session[SESSION_GENERATION] = user.session_generation


class SessionPolicyMiddleware:
    """Absolute session lifetime and server-side revocation.

    A session ends 12 hours after sign-in regardless of activity, and every
    session for a user ends when their session generation changes (password
    reset, account disable).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            auth_at = request.session.get(SESSION_AUTH_AT)
            generation = request.session.get(SESSION_GENERATION)
            limit = settings.SESSION_ABSOLUTE_LIFETIME.total_seconds()
            expired = auth_at is None or (timezone.now().timestamp() - auth_at) > limit
            revoked = generation != user.session_generation or not user.is_active
            if expired or revoked:
                logout(request)
                return redirect(f"{reverse('accounts:sign_in')}?ended=1")
        return self.get_response(request)


class SecurityHeadersMiddleware:
    """CSP for every response; no-store for anything served to a signed-in user."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        is_static = request.path.startswith(settings.STATIC_URL)
        if not is_static and (request.user.is_authenticated if hasattr(request, "user") else False):
            response["Cache-Control"] = "no-store"
        elif not is_static:
            response.setdefault("Cache-Control", "no-cache")
        return response
