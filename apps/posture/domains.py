from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from django.views.decorators.http import require_http_methods, require_POST

from apps.core import audit, tenancy, tokens
from apps.workspaces.access import workspace_view
from apps.workspaces.models import Membership, Workspace

from .dns_records import query_txt, summarize
from .forms import DomainForm
from .models import Action, DnsCooldown, DnsPermit, Domain, DomainJob
from .services import lock_workspace, record_finding

ACTIVE = (DomainJob.Status.QUEUED, DomainJob.Status.RUNNING)
PROOF_WINDOW = timedelta(hours=48)
VERIFIED_WINDOW = timedelta(days=30)
LEASE_WINDOW = timedelta(seconds=20)


class DomainUnavailable(Exception):
    pass


def challenge(domain):
    value = f"{domain.workspace_id}:{domain.pk}:{domain.name}:{domain.proof_generation}"
    return "aegisone=" + salted_hmac("aegisone.dns-proof.v1", value, algorithm="sha256").hexdigest()


def verified(domain, now):
    return domain.revoked_at is None and domain.verified_until is not None and domain.verified_until > now


def eligible(domain, kind, now):
    if domain.revoked_at:
        return False
    if kind == DomainJob.Kind.VERIFY:
        return domain.challenge_expires_at > now and not verified(domain, now)
    return verified(domain, now)


def feature_on():
    if not settings.DNS_CHECKS_ENABLED:
        raise PermissionDenied


def cancel_jobs(workspace, domain):
    DomainJob.objects.filter(workspace=workspace, domain=domain, status__in=ACTIVE).update(
        status=DomainJob.Status.CANCELLED, result="Domain authorization changed.", finished_at=timezone.now(),
    )


def expire_jobs(workspace, now):
    jobs = DomainJob.objects.filter(workspace=workspace)
    jobs.filter(status=DomainJob.Status.RUNNING, lease_until__lte=now).update(
        status=DomainJob.Status.INCONCLUSIVE, result="The worker did not finish in time. Try again.", finished_at=now,
    )
    jobs.filter(status=DomainJob.Status.QUEUED, created_at__lte=now - timedelta(hours=1)).update(
        status=DomainJob.Status.INCONCLUSIVE, result="The queue did not reach this request in time. Try again.", finished_at=now,
    )


@require_http_methods(["GET", "POST"])
@workspace_view()
def domain_list(request):
    form = DomainForm(request.POST if request.method == "POST" else None)
    items = Domain.objects.filter(workspace=request.workspace)
    if request.method == "POST":
        feature_on()
        if not request.membership.is_owner:
            raise PermissionDenied
        if form.is_valid():
            lock_workspace(request.workspace)
            if items.filter(name=form.cleaned_data["name"]).exists():
                form.add_error("name", "This domain is already listed. Open its details to manage it.")
            elif items.count() >= 5:
                form.add_error("name", "This workspace has reached its five-domain limit.")
            else:
                now = timezone.now()
                domain = Domain.objects.create(
                    workspace=request.workspace, name=form.cleaned_data["name"], sends_mail=form.cleaned_data["sends_mail"],
                    attested_by=request.user, attested_at=now, challenge_expires_at=now + PROOF_WINDOW,
                )
                audit.record("domain.attested", actor=request.user, workspace=request.workspace, target=domain.pk)
                return redirect("posture:domain_detail", domain_id=domain.pk)
    now = timezone.now()
    return render(request, "posture/domains.html", {
        "nav": "domains", "items": [(item, verified(item, now)) for item in items],
        "form": form, "enabled": settings.DNS_CHECKS_ENABLED,
    }, status=400 if request.method == "POST" else 200)


@require_http_methods(["GET", "POST"])
@workspace_view()
def domain_detail(request, domain_id):
    domain = get_object_or_404(Domain, workspace=request.workspace, pk=domain_id)
    now = timezone.now()
    if request.method == "POST":
        feature_on()
        if not request.membership.is_owner:
            raise PermissionDenied
        lock_workspace(request.workspace)
        domain.refresh_from_db()
        operation = request.POST.get("operation")
        if operation in DomainJob.Kind.values:
            try:
                queue_job(request.workspace, domain, request.user, operation, now)
            except DomainUnavailable as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Request queued. Open this page again to check its status.")
        elif operation == "renew" and request.POST.get("attest") == "1":
            cancel_jobs(request.workspace, domain)
            domain.proof_generation += 1
            domain.attested_by = request.user
            domain.attested_at = now
            domain.challenge_expires_at = now + PROOF_WINDOW
            domain.verified_until = None
            domain.revoked_at = None
            domain.save()
            audit.record("domain.renewed", actor=request.user, workspace=request.workspace, target=domain.pk)
            messages.success(request, "Publish the new TXT value before requesting verification.")
        else:
            messages.error(request, "Choose a domain operation and confirm authorization where required.")
        return redirect("posture:domain_detail", domain_id=domain.pk)

    may_manage = request.membership.is_owner and settings.DNS_CHECKS_ENABLED
    last = domain.jobs.filter(kind=DomainJob.Kind.CHECK, finished_at__gte=now - timedelta(days=90)).exclude(observations=[]).first()
    return render(request, "posture/domain.html", {
        "nav": "domains", "domain": domain, "may_manage": may_manage, "verified": verified(domain, now),
        "can_verify": eligible(domain, DomainJob.Kind.VERIFY, now), "latest_job": domain.jobs.first(),
        "observed": last, "challenge": challenge(domain) if may_manage else "",
    })


@require_POST
@workspace_view(owner_only=True)
def domain_revoke(request, domain_id):
    lock_workspace(request.workspace)
    domain = get_object_or_404(Domain, workspace=request.workspace, pk=domain_id)
    if not domain.revoked_at:
        domain.revoked_at = timezone.now()
        domain.verified_until = None
        domain.proof_generation += 1
        domain.save(update_fields=["revoked_at", "verified_until", "proof_generation"])
        cancel_jobs(request.workspace, domain)
        Action.objects.filter(workspace=request.workspace, key__in=[f"SPF:{domain.pk}", f"DMARC:{domain.pk}"]).update(
            current_gap=False,
        )
        audit.record("domain.revoked", actor=request.user, workspace=request.workspace, target=domain.pk)
    messages.success(request, "Domain authorization revoked.")
    return redirect("posture:domain_detail", domain_id=domain.pk)


def queue_job(workspace, domain, actor, kind, now):
    if not eligible(domain, kind, now):
        raise DomainUnavailable("This operation requires a valid TXT challenge or verified domain.")
    expire_jobs(workspace, now)
    jobs = DomainJob.objects.filter(workspace=workspace)
    if jobs.filter(status__in=ACTIVE).exists():
        raise DomainUnavailable("This workspace already has a DNS request in progress.")
    maximum = 10 if kind == DomainJob.Kind.VERIFY else 5
    if jobs.filter(kind=kind, created_at__gt=now - timedelta(days=1)).count() >= maximum:
        raise DomainUnavailable("The DNS request limit for the past 24 hours has been reached.")
    job = DomainJob.objects.create(
        workspace=workspace, domain=domain, actor=actor, kind=kind, proof_generation=domain.proof_generation,
    )
    audit.record("domain.job_queued", actor=actor, workspace=workspace, target=job.pk)
    return job


def still_authorized(job, now):
    tenancy.set_user(job.actor_id)
    return (
        settings.DNS_CHECKS_ENABLED
        and job.workspace.status == Workspace.ACTIVE
        and job.domain.proof_generation == job.proof_generation
        and eligible(job.domain, job.kind, now)
        and Membership.objects.filter(
            workspace_id=job.workspace_id, user_id=job.actor_id, user__is_active=True,
            revoked_at__isnull=True, role=Membership.OWNER,
        ).exists()
    )


def finish(job, status, result, now, observations=None):
    job.status = status
    job.result = result
    job.finished_at = now
    job.observations = observations or []
    job.save(update_fields=["status", "result", "finished_at", "observations"])


@transaction.atomic
def claim(workspace_id):
    if not settings.DNS_CHECKS_ENABLED:
        return None
    tenancy.set_workspace(workspace_id)
    workspace = Workspace.objects.filter(pk=workspace_id, status=Workspace.ACTIVE).first()
    if workspace is None:
        return None
    lock_workspace(workspace, allow_closed=True)
    workspace.refresh_from_db(fields=["status"])
    if workspace.status != Workspace.ACTIVE:
        return None
    now = timezone.now()
    expire_jobs(workspace, now)
    job = DomainJob.objects.filter(workspace=workspace, status=DomainJob.Status.QUEUED).select_related("domain").first()
    if job is None:
        return None
    if not still_authorized(job, now):
        finish(job, DomainJob.Status.CANCELLED, "The request is no longer authorized.", now)
        return None
    DnsPermit.objects.bulk_create([DnsPermit(slot=slot, available_at=now) for slot in (1, 2)], ignore_conflicts=True)
    permit = DnsPermit.objects.filter(available_at__lte=now).order_by("slot").select_for_update(skip_locked=True).first()
    if permit is None:
        return None
    if job.kind == DomainJob.Kind.CHECK:
        key = tokens.digest(job.domain.name)
        cooldown, _ = DnsCooldown.objects.select_for_update().get_or_create(name_digest=key, defaults={"available_at": now})
        if cooldown.available_at > now:
            finish(job, DomainJob.Status.CANCELLED, "This exact DNS name was recently checked. Wait an hour and try again.", now)
            return None
        cooldown.available_at = now + timedelta(hours=1)
        cooldown.save(update_fields=["available_at"])
    job.lease_until = now + LEASE_WINDOW
    job.status = DomainJob.Status.RUNNING
    job.save(update_fields=["status", "lease_until"])
    permit.available_at = job.lease_until
    permit.job_id = job.pk
    permit.save(update_fields=["available_at", "job_id"])
    return job


@transaction.atomic
def publish(job, proof_status, observations):
    tenancy.set_workspace(job.workspace_id)
    lock_workspace(job.workspace, allow_closed=True)
    stored = DomainJob.objects.select_related("domain").get(workspace_id=job.workspace_id, pk=job.pk)
    permit = DnsPermit.objects.select_for_update().filter(job_id=job.pk).first()
    now = timezone.now()
    if permit:
        permit.available_at = now
        permit.job_id = None
        permit.save(update_fields=["available_at", "job_id"])
    if stored.status != DomainJob.Status.RUNNING or not permit:
        return
    if stored.lease_until <= now or not still_authorized(stored, now):
        finish(stored, DomainJob.Status.CANCELLED, "Authorization or the worker lease expired.", now)
        return
    if stored.kind == DomainJob.Kind.VERIFY:
        if proof_status is True:
            stored.domain.verified_until = now + VERIFIED_WINDOW
            stored.domain.save(update_fields=["verified_until"])
            audit.record("domain.verified", actor=stored.actor, workspace=stored.workspace, target=stored.domain.pk)
            finish(stored, DomainJob.Status.COMPLETE, "TXT proof verified.", now)
        else:
            outcome = "The resolver could not verify the exact TXT name." if proof_status is None else "The expected TXT proof was not found."
            finish(stored, DomainJob.Status.INCONCLUSIVE, outcome, now)
        return

    status = DomainJob.Status.INCONCLUSIVE if all(item["status"] == "inconclusive" for item in observations) else DomainJob.Status.COMPLETE
    finish(stored, status, "DNS results recorded.", now, observations)
    if not stored.domain.sends_mail:
        return
    for evidence in observations:
        kind = evidence["kind"]
        if evidence["status"] == "inconclusive":
            continue
        gap = evidence["status"] in ("missing", "needs_review")
        key = f"{kind}:{stored.domain_id}"
        action = Action.objects.filter(workspace=stored.workspace, key=key).first()
        if action is None and not gap:
            continue
        record_finding(
            stored.workspace, stored.actor, action, key=key, title=f"Review {kind} for {stored.domain.name}", priority=2,
            reason=evidence["detail"], steps="Ask your email provider to review the record before changing policy.",
            confirmation="Review the provider's advice and run another exact-name check.", guidance_version=1,
            source_kind="dns", source_id=stored.pk, observed_at=now, gap=gap,
        )


def run_pending(workspace_id, resolver=query_txt):
    job = claim(workspace_id)
    if job is None:
        return False
    proof_status = None
    observations = []
    if job.kind == DomainJob.Kind.VERIFY:
        records = resolver("_aegisone-challenge." + job.domain.name)
        if records is not None:
            expected = challenge(job.domain).encode("ascii")
            proof_status = any(constant_time_compare(record, expected) for record in records)
    else:
        for kind, name in (("SPF", job.domain.name), ("DMARC", "_dmarc." + job.domain.name)):
            status, detail = summarize(kind, resolver(name))
            observations.append({"kind": kind, "status": status, "label": status.replace("_", " ").capitalize(), "detail": detail})
    publish(job, proof_status, observations)
    return True
