import hashlib
import json
from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.core import audit
from apps.workspaces.access import workspace_view

from .catalog import CATALOGS, CHOICES
from .forms import DataRequestForm, ReportForm
from .models import Action, DataRequest, DomainJob, ExportPayload, Report
from .notifications import notify_data_request
from .services import latest_assessment, lock_workspace


def build_snapshot(workspace):
    assessment = latest_assessment(workspace)
    if assessment is None:
        return None
    answers = dict(CHOICES)
    return {
        "workspace": workspace.name,
        "assessment_id": str(assessment.pk),
        "submitted_at": assessment.submitted_at.isoformat(),
        "submitted_label": timezone.localtime(assessment.submitted_at).strftime("%d %b %Y, %H:%M %Z"),
        "catalog_version": assessment.template_version,
        "score": assessment.score,
        "unsure_count": assessment.unsure_count,
        "answers": [
            {"prompt": item.prompt, "answer": answers[assessment.answers[item.key]]}
            for item in CATALOGS[assessment.template_version]
        ],
        "actions": [
            {
                "title": item.title, "priority": item.get_priority_display(), "status": item.get_status_display(),
                "reason": item.reason, "steps": item.steps, "confirmation": item.confirmation, "source": item.source_kind,
            }
            for item in Action.objects.filter(workspace=workspace, current_gap=True)
        ],
        "domain_observations": domain_observations(workspace),
    }


def domain_observations(workspace):
    cutoff = timezone.now() - timedelta(days=90)
    jobs = DomainJob.objects.filter(
        workspace=workspace, domain__revoked_at__isnull=True, kind=DomainJob.Kind.CHECK, finished_at__gte=cutoff,
    ).exclude(observations=[]).select_related("domain").order_by("domain_id", "-finished_at", "-pk").distinct("domain_id")
    return [
        {
            "name": job.domain.name, "observed_at": job.finished_at.isoformat(),
            "observed_label": timezone.localtime(job.finished_at).strftime("%d %b %Y, %H:%M %Z"),
            "observations": job.observations,
        }
        for job in sorted(jobs, key=lambda job: (job.finished_at, job.domain.name), reverse=True)
    ]


def fingerprint(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@require_GET
@workspace_view()
def reports(request):
    items = Report.objects.filter(workspace=request.workspace, revoked_at__isnull=True).order_by("-created_at", "-pk")
    return render(request, "posture/reports.html", {"nav": "reports", "items": items, "latest": latest_assessment(request.workspace)})


@require_http_methods(["GET", "POST"])
@workspace_view()
def report_preview(request):
    if request.method == "POST":
        lock_workspace(request.workspace)
        request.workspace.refresh_from_db(fields=["name"])
    snapshot = build_snapshot(request.workspace)
    if snapshot is None:
        messages.error(request, "Submit an assessment before creating a report.")
        return redirect("posture:reports")
    version = fingerprint(snapshot)
    if request.method == "POST":
        form = ReportForm(request.POST)
        if form.is_valid() and form.cleaned_data["version"] == version:
            report = Report.objects.create(workspace=request.workspace, created_by=request.user, snapshot=snapshot)
            audit.record("report.created", actor=request.user, workspace=request.workspace, target=report.pk)
            messages.success(request, "Report saved.")
            return redirect("posture:report", report_id=report.pk)
        messages.error(request, "The workspace changed. Review this updated preview before saving.")
    return render(request, "posture/report.html", {
        "nav": "reports", "snapshot": snapshot, "form": ReportForm(initial={"version": version}),
    }, status=409 if request.method == "POST" else 200)


@require_GET
@workspace_view()
def report_detail(request, report_id):
    report = get_object_or_404(Report, workspace=request.workspace, pk=report_id, revoked_at__isnull=True)
    return render(request, "posture/report.html", {
        "nav": "reports", "snapshot": report.snapshot, "report": report,
        "can_revoke": request.membership.is_owner or report.created_by_id == request.user.pk,
    })


@require_POST
@workspace_view()
def report_revoke(request, report_id):
    report = get_object_or_404(Report.objects.select_for_update(), workspace=request.workspace, pk=report_id, revoked_at__isnull=True)
    if not request.membership.is_owner and report.created_by_id != request.user.pk:
        raise PermissionDenied
    report.revoked_at = timezone.now()
    report.save(update_fields=["revoked_at"])
    audit.record("report.revoked", actor=request.user, workspace=request.workspace, target=report.pk)
    messages.success(request, "Report access revoked.")
    return redirect("posture:reports")


@require_http_methods(["GET", "POST"])
@workspace_view(owner_only=True)
def data_requests(request):
    items = DataRequest.objects.filter(workspace=request.workspace).select_related("export_payload").defer(
        "export_payload__payload",
    ).order_by("-created_at", "-pk")
    if request.method == "POST":
        form = DataRequestForm(request.POST)
        if form.is_valid():
            kind = form.cleaned_data["kind"]
            with transaction.atomic():
                lock_workspace(request.workspace)
                active = items.filter(kind=kind, status__in=[DataRequest.Status.RECEIVED, DataRequest.Status.IN_REVIEW]).first()
                if active is None:
                    active = DataRequest.objects.create(workspace=request.workspace, requested_by=request.user, kind=kind)
                    audit.record("data_request.received", actor=request.user, workspace=request.workspace, target=active.pk)
                    notify_data_request(request.user.email, active.get_kind_display(), active.get_status_display())
            messages.success(request, "Request received. You can track it on this page.")
            return redirect("posture:data_requests")
        messages.error(request, "Confirm the workspace request before submitting.")
    now = timezone.now()
    return render(request, "posture/data_requests.html", {
        "nav": "settings", "items": items, "kinds": DataRequest.Kind.choices, "now": now,
    }, status=400 if request.method == "POST" else 200)


@require_GET
@workspace_view(owner_only=True)
def data_export(request, request_id):
    export = get_object_or_404(
        ExportPayload, workspace=request.workspace, request_id=request_id, request__requested_by=request.user,
        request__status=DataRequest.Status.COMPLETED, expires_at__gt=timezone.now(),
    )
    audit.record("data_request.downloaded", actor=request.user, workspace=request.workspace, target=request_id)
    response = JsonResponse(export.payload, json_dumps_params={"indent": 2})
    response.headers["Content-Disposition"] = 'attachment; filename="aegisone-workspace-export.json"'
    return response
