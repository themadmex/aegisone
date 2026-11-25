from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit

from apps.posture.models import Action
from apps.posture.reports import domain_observations
from apps.posture.services import draft_for, latest_assessment

from . import services
from .access import SESSION_WORKSPACE, workspace_view
from .forms import InviteForm
from .models import Invitation, Membership


@require_GET
@workspace_view()
def overview(request):
    return render(request, "workspaces/overview.html", {
        "nav": "overview",
        "draft": draft_for(request.workspace),
        "latest": latest_assessment(request.workspace),
        "top_actions": Action.objects.filter(workspace=request.workspace, current_gap=True).exclude(status=Action.Status.DONE)[:3],
        "recent_domains": domain_observations(request.workspace)[:3],
    })


def _members_context(request, form=None):
    now = timezone.now()
    members = (
        Membership.objects.select_related("user")
        .filter(workspace=request.workspace, revoked_at__isnull=True)
        .order_by("-role", "user__name")
    )
    pending = Invitation.objects.filter(
        workspace=request.workspace, consumed_at__isnull=True, retired_at__isnull=True, expires_at__gt=now
    ).order_by("created_at")
    return {
        "nav": "settings",
        "settings_nav": "members",
        "members": members,
        "pending": pending,
        "form": form or InviteForm(),
    }


@require_GET
@workspace_view(owner_only=True)
def members(request):
    return render(request, "workspaces/members.html", _members_context(request))


@require_POST
@ratelimit(key="user", rate="30/h", block=True)
@workspace_view(owner_only=True)
def invite(request):
    form = InviteForm(request.POST)
    if form.is_valid():
        email = form.cleaned_data["email"]
        try:
            services.invite(request.workspace, email, "contributor", request.user)
        except services.AlreadyMemberError:
            form.add_error("email", "This person is already a member of this workspace.")
        else:
            messages.success(request, f"Invite sent to {email}. The link works once and expires in 48 hours.")
            return redirect("workspaces:members")
    return render(request, "workspaces/members.html", _members_context(request, form), status=400)


@require_POST
@ratelimit(key="user", rate="30/h", block=True)
@workspace_view(owner_only=True)
def resend_invite(request, invitation_id):
    try:
        email, _ = services.resend(request.workspace, invitation_id, request.user)
    except (Invitation.DoesNotExist, services.InvitationUnavailable):
        raise Http404 from None
    messages.success(request, f"A fresh link was sent to {email}. The old link no longer works.")
    return redirect("workspaces:members")


@require_POST
@workspace_view(owner_only=True)
def cancel_invite(request, invitation_id):
    if not services.cancel(request.workspace, invitation_id, request.user):
        raise Http404
    messages.success(request, "Invite cancelled.")
    return redirect("workspaces:members")


@require_POST
@workspace_view(owner_only=True)
def remove_member(request, membership_id):
    try:
        removed = services.remove_member(request.workspace, membership_id, request.user)
    except Membership.DoesNotExist:
        raise Http404 from None
    except services.LastOwnerError:
        messages.error(request, "A workspace must keep at least one owner. Contact support to hand over ownership.")
        return redirect("workspaces:members")
    messages.success(request, f"{removed.user.display_name} was removed.")
    if removed.user_id == request.user.id:
        return redirect("workspaces:overview")
    return redirect("workspaces:members")


@require_POST
@workspace_view()
def switch(request):
    wanted = request.POST.get("workspace_id", "")
    if not any(str(m.workspace_id) == wanted for m in request.memberships):
        raise Http404
    request.session[SESSION_WORKSPACE] = wanted
    return redirect("workspaces:overview")
