from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import normalize_email
from apps.core import audit, tenancy
from apps.workspaces.models import Membership, Workspace

from .catalog import CATALOGS
from .models import Action, DataRequest, Domain, DomainJob, ExportPayload, Report
from .notifications import notify_data_request
from .reports import domain_observations
from .services import assessments, lock_workspace


@transaction.atomic
def review_request(workspace_id, request_id, verified_owner, decision):
    tenancy.set_workspace(workspace_id)
    workspace = Workspace.objects.get(pk=workspace_id)
    lock_workspace(workspace, allow_closed=True)
    workspace.refresh_from_db(fields=["status"])
    request = DataRequest.objects.select_related("requested_by").get(workspace=workspace, pk=request_id)
    owner = request.requested_by
    if (
        workspace.status != Workspace.ACTIVE
        or request.status not in (DataRequest.Status.RECEIVED, DataRequest.Status.IN_REVIEW)
        or not owner.is_active
        or normalize_email(verified_owner) != owner.email
        or not Membership.objects.filter(
            workspace=workspace, user=owner, role=Membership.OWNER, revoked_at__isnull=True,
        ).exists()
    ):
        raise ValueError("This request has no active, verified requester.")
    allowed = {"review", "decline", request.kind}
    if decision not in allowed:
        raise ValueError("Decision does not match the workspace request.")

    now = timezone.now()
    if decision == DataRequest.Kind.EXPORT:
        payload = export_workspace(workspace)
        ExportPayload.objects.create(workspace=workspace, request=request, payload=payload, expires_at=now + timedelta(days=7))
    elif decision == DataRequest.Kind.CLOSURE:
        workspace.status = Workspace.CLOSED
        workspace.save(update_fields=["status"])
        DomainJob.objects.filter(workspace=workspace, status__in=["queued", "running"]).update(
            status=DomainJob.Status.CANCELLED, result="Workspace closed.", finished_at=now,
        )
        Domain.objects.filter(workspace=workspace, revoked_at__isnull=True).update(revoked_at=now, verified_until=None)
        Report.objects.filter(workspace=workspace, revoked_at__isnull=True).update(revoked_at=now)
        ExportPayload.objects.filter(workspace=workspace, expires_at__gt=now).update(expires_at=now)
    request.status = {
        "review": DataRequest.Status.IN_REVIEW, "decline": DataRequest.Status.DECLINED,
        DataRequest.Kind.EXPORT: DataRequest.Status.COMPLETED, DataRequest.Kind.CLOSURE: DataRequest.Status.COMPLETED,
    }[decision]
    request.save(update_fields=["status"])
    audit.record(f"data_request.{decision}", workspace=workspace, target=request.pk)
    notify_data_request(owner.email, request.get_kind_display(), request.get_status_display(), link_available=workspace.status == Workspace.ACTIVE)
    return request


def export_workspace(workspace):
    return {
        "version": 1,
        "workspace": workspace.name,
        "assessments": [
            {
                "catalog_version": row.template_version,
                "submitted_at": row.submitted_at.isoformat(),
                "score": row.score,
                "unsure_count": row.unsure_count,
                "answers": [
                    {"key": item.key, "question": item.prompt, "answer": row.answers[item.key]}
                    for item in CATALOGS[row.template_version]
                ],
            }
            for row in assessments(workspace).filter(submitted_at__isnull=False).order_by("submitted_at", "id")
        ],
        "actions": list(Action.objects.filter(workspace=workspace).values(
            "key", "title", "priority", "status", "current_gap", "reason", "source_kind"
        )),
        "domain_observations": domain_observations(workspace),
    }
