from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core import tenancy

from . import services

SESSION_WORKSPACE = "aegis_workspace_id"


def workspace_view(owner_only=False):
    """Authorise a request against the user's current membership.

    Runs inside the request transaction (ATOMIC_REQUESTS). Requires a signed-in,
    MFA-verified user, re-reads membership from the database on every request
    (so removal takes effect on the next click), then scopes the database to the
    chosen workspace. Nothing from the browser decides the role.
    """

    def decorator(view):
        @wraps(view)
        def inner(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect(f"{reverse('accounts:sign_in')}?next={request.path}")
            if not user.is_verified():
                return redirect("accounts:mfa")

            tenancy.set_user(user.id)
            memberships = services.active_memberships(user)
            if not memberships:
                return render(request, "workspaces/no_access.html", status=403)

            wanted = request.session.get(SESSION_WORKSPACE)
            current = next((m for m in memberships if str(m.workspace_id) == wanted), memberships[0])
            request.session[SESSION_WORKSPACE] = str(current.workspace_id)
            tenancy.set_workspace(current.workspace_id)

            if owner_only and not current.is_owner:
                raise PermissionDenied

            request.workspace = current.workspace
            request.membership = current
            request.memberships = memberships
            return view(request, *args, **kwargs)

        return inner

    return decorator
