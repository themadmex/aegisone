from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import StringIO

import psycopg
import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.urls import reverse
from django.utils import timezone

from apps.core import tenancy
from apps.posture import catalog, domains, services
from apps.posture.dns_records import normalize_domain, summarize
from apps.posture.models import (
    Action,
    Assessment,
    DataRequest,
    Domain,
    DomainJob,
    ExportPayload,
    Report,
)
from apps.posture.rights import review_request
from apps.workspaces.models import Membership, Workspace

from .conftest import add_member, make_user, sign_in_verified

pytestmark = pytest.mark.django_db(transaction=True)


def prepare_assessment(workspace, owner, answers):
    with transaction.atomic():
        tenancy.set_workspace(workspace.pk)
        row = services.start_assessment(workspace, owner)
        row.answers = answers
        row.revision += 1
        row.save(update_fields=["answers", "revision"])
    return row


def answers_with(default="yes", **overrides):
    return {item.key: overrides.get(item.key, default) for item in catalog.CATALOGS[catalog.CURRENT_VERSION]}


def submit(workspace, owner, draft):
    with transaction.atomic():
        tenancy.set_workspace(workspace.pk)
        return services.submit_assessment(workspace, owner, draft.pk, draft.revision)


@pytest.mark.parametrize(("answers", "expected"), [
    (answers_with(), 100),
    (answers_with("unsure", Q01="yes", Q02="yes", Q03="yes", Q04="partly"), 18),
    (answers_with("unsure"), 0),
])
def test_score_golden_fixtures(answers, expected):
    assert catalog.score(answers, catalog.CATALOGS[1]) == expected


def test_assessment_resume_stale_write_and_submission_replay(client, workspace_factory):
    workspace, owner = workspace_factory("Alpha", "owner@alpha.example")
    sign_in_verified(client, owner)
    assert client.post(reverse("posture:assessment_start")).status_code == 302
    with transaction.atomic():
        tenancy.set_workspace(workspace.pk)
        draft = Assessment.objects.get()
    first = reverse("posture:question", args=[draft.pk, "Q01"])
    assert client.post(first, {"revision": 0, "answer": "no"}).status_code == 302
    stale = client.post(first, {"revision": 0, "answer": "yes"}, follow=True)
    assert b"changed in another tab" in stale.content
    assert client.get(reverse("posture:assessment"))["Location"].endswith("/question/Q02")
    with pytest.raises(services.Conflict), transaction.atomic():
        tenancy.set_workspace(workspace.pk)
        services.submit_assessment(workspace, owner, draft.pk, 1)

    draft = prepare_assessment(workspace, owner, answers_with(Q01="no"))
    def run_submit():
        close_old_connections()
        try:
            return submit(workspace, owner, draft).pk
        finally:
            close_old_connections()

    with ThreadPoolExecutor(2) as pool:
        assert list(pool.map(lambda _: run_submit(), range(2))) == [draft.pk, draft.pk]
    with transaction.atomic():
        tenancy.set_workspace(workspace.pk)
        assert Assessment.objects.get().score == 95
        assert Action.objects.get().history.count() == 1
        with pytest.raises(IntegrityError), transaction.atomic():
            Assessment.objects.filter(pk=draft.pk).update(score=0)


def test_action_recurrence_and_stale_revision(workspace_factory):
    workspace, owner = workspace_factory("Alpha", "owner@alpha.example")
    initial = submit(workspace, owner, prepare_assessment(workspace, owner, answers_with(Q02="partly", Q01="no")))
    with transaction.atomic():
        tenancy.set_workspace(workspace.pk)
        first, second = Action.objects.all()
        assert (first.key, second.key) == ("Q01", "Q02")
        done = services.transition_action(workspace, owner, first.pk, first.revision, "done")
        with pytest.raises(services.Conflict):
            services.transition_action(workspace, owner, first.pk, first.revision, "open")
        services.submit_assessment(workspace, owner, initial.pk, initial.revision)
        done.refresh_from_db()
        assert done.status == "done"
    submit(workspace, owner, prepare_assessment(workspace, owner, answers_with(Q01="unsure")))
    with transaction.atomic():
        tenancy.set_workspace(workspace.pk)
        first.refresh_from_db()
        second.refresh_from_db()
        assert first.status == "open" and first.history.filter(event="reopened").count() == 1
        assert not second.current_gap


def test_scoped_report_stale_preview_revocation_and_export(client, workspace_factory):
    alpha, owner = workspace_factory("Alpha", "owner@alpha.example")
    beta, beta_owner = workspace_factory("Beta", "owner@beta.example")
    contributor = make_user("contributor@alpha.example")
    add_member(alpha, contributor, Membership.CONTRIBUTOR)
    outsider = sign_in_verified(client.__class__(), beta_owner)
    team_member = sign_in_verified(client.__class__(), contributor)
    sign_in_verified(client, owner)
    first = submit(alpha, owner, prepare_assessment(alpha, owner, answers_with(Q01="no")))
    submit(beta, beta_owner, prepare_assessment(beta, beta_owner, answers_with("unsure")))
    assert outsider.get(reverse("posture:assessment_review", args=[first.pk])).status_code == 404

    preview = reverse("posture:report_preview")
    stale = client.get(preview).context["form"].initial["version"]
    submit(alpha, owner, prepare_assessment(alpha, owner, answers_with()))
    assert client.post(preview, {"version": stale}).status_code == 409
    snapshot = client.get(preview).context["form"].initial["version"]
    report_url = client.post(preview, {"version": snapshot})["Location"]
    submit(alpha, owner, prepare_assessment(alpha, owner, answers_with("unsure")))
    report = client.get(report_url)
    assert report.status_code == 200 and report.context["snapshot"]["score"] == 100
    assert report["Cache-Control"] == "no-store"
    assert outsider.get(report_url).status_code == 404
    assert team_member.get(report_url).status_code == 200
    with transaction.atomic():
        tenancy.set_workspace(alpha.pk)
        report_id = Report.objects.get().pk
        with pytest.raises(IntegrityError), transaction.atomic():
            Report.objects.filter(pk=report_id).update(snapshot={})

    revoke = reverse("posture:report_revoke", args=[report_id])
    assert team_member.post(revoke).status_code == 403
    assert client.post(revoke).status_code == 302
    assert client.get(report_url).status_code == 404

    rights = reverse("posture:data_requests")
    assert team_member.post(rights, {"kind": "export", "confirmed": "on"}).status_code == 403
    for _ in range(2):
        assert client.post(rights, {"kind": "export", "confirmed": "on"}).status_code == 302
    with transaction.atomic():
        tenancy.set_workspace(alpha.pk)
        request = DataRequest.objects.get()
    with pytest.raises(ValueError):
        review_request(alpha.pk, request.pk, beta_owner.email, "export")
    review_request(alpha.pk, request.pk, owner.email, "export")
    url = reverse("posture:data_export", args=[request.pk])
    export = client.get(url)
    assert export.status_code == 200 and len(export.json()["assessments"]) == 3
    assert b"Beta" not in export.content and owner.email.encode() not in export.content
    assert outsider.get(url).status_code == 404
    assert team_member.get(url).status_code == 403
    with transaction.atomic():
        tenancy.set_workspace(alpha.pk)
        ExportPayload.objects.filter(request=request).update(expires_at=timezone.now() - timedelta(seconds=1))
    assert client.get(url).status_code == 404


def test_closure_revokes_workspace_access(client, workspace_factory):
    workspace, owner = workspace_factory("Alpha", "owner@alpha.example")
    sign_in_verified(client, owner)
    url = reverse("posture:data_requests")
    assert client.post(url, {"kind": "closure", "confirmed": "on"}).status_code == 302
    with transaction.atomic():
        tenancy.set_workspace(workspace.pk)
        request = DataRequest.objects.get()
    review_request(workspace.pk, request.pk, owner.email, "closure")
    assert client.get(reverse("workspaces:overview")).status_code == 403
    assert client.get(reverse("posture:assessment")).status_code == 403
    with transaction.atomic():
        tenancy.set_workspace(workspace.pk)
        assert Workspace.objects.get().status == Workspace.CLOSED


def test_retention_preview_and_cleanup_are_workspace_scoped(workspace_factory):
    alpha, alpha_owner = workspace_factory("Alpha", "owner@alpha.example")
    beta, beta_owner = workspace_factory("Beta", "owner@beta.example")
    for workspace, user in [(alpha, alpha_owner), (beta, beta_owner)]:
        with transaction.atomic():
            tenancy.set_workspace(workspace.pk)
            Report.objects.create(workspace=workspace, created_by=user, snapshot={}, revoked_at=timezone.now() - timedelta(days=31))
    output = StringIO()
    call_command("prune_workspace_artifacts", workspace=alpha.pk, stdout=output)
    assert "Preview" in output.getvalue() and "1 revoked reports" in output.getvalue()
    with transaction.atomic():
        tenancy.set_workspace(alpha.pk)
        assert Report.objects.count() == 1
    call_command("prune_workspace_artifacts", workspace=alpha.pk, apply=True, stdout=output)
    with transaction.atomic():
        tenancy.set_workspace(alpha.pk)
        assert Report.objects.count() == 0
        tenancy.set_workspace(beta.pk)
        assert Report.objects.count() == 1


def test_dns_proof_timeout_fixed_queries_and_revoked_lease(client, workspace_factory, settings):
    settings.DNS_CHECKS_ENABLED = True
    workspace, owner = workspace_factory("Alpha", "owner@alpha.example")
    member = make_user("member@alpha.example")
    add_member(workspace, member, Membership.CONTRIBUTOR)
    contributor = sign_in_verified(client.__class__(), member)
    sign_in_verified(client, owner)
    url = reverse("posture:domains")
    data = {"name": "company.com", "sends_mail": "on", "attest": "on"}
    assert contributor.post(url, data).status_code == 403
    assert client.post(url, {**data, "name": "127.0.0.1"}).status_code == 400
    response = client.post(url, data, follow=True)
    detail_url = response.redirect_chain[0][0]
    assert client.post(detail_url, {"operation": "check"}, follow=True).context["messages"]
    with transaction.atomic():
        tenancy.set_workspace(workspace.pk)
        domain = Domain.objects.get()
        proof = domains.challenge(domain).encode()
        assert DomainJob.objects.count() == 0
    assert client.post(detail_url, {"operation": "verify"}).status_code == 302
    queried = []
    def verification(name):
        queried.append(name)
        return [proof]
    assert domains.run_pending(workspace.pk, resolver=verification)
    assert queried == ["_aegisone-challenge.company.com"]
    assert client.post(detail_url, {"operation": "check"}).status_code == 302

    def first_check(name):
        queried.append(name)
        return None if name.startswith("_dmarc.") else (b"v=spf1 ~all", b"v=spf1 -all")
    assert domains.run_pending(workspace.pk, resolver=first_check)
    assert queried[-2:] == ["company.com", "_dmarc.company.com"]
    with transaction.atomic():
        tenancy.set_workspace(workspace.pk)
        result = DomainJob.objects.filter(kind="check").first()
        assert [row["status"] for row in result.observations] == ["needs_review", "inconclusive"]
        assert Action.objects.filter(source_kind="dns").count() == 1
    overview = client.get(reverse("workspaces:overview"))
    assert overview.context["recent_domains"][0]["name"] == "company.com"

    with transaction.atomic():
        tenancy.set_workspace(workspace.pk)
        DomainJob.objects.filter(kind="check").update(finished_at=timezone.now() - timedelta(hours=2))
        from apps.posture.models import DnsCooldown
        DnsCooldown.objects.update(available_at=timezone.now() - timedelta(seconds=1))
    assert client.post(detail_url, {"operation": "check"}).status_code == 302
    def revoke_mid_request(name):
        if not name.startswith("_dmarc."):
            assert client.post(reverse("posture:domain_revoke", args=[domain.pk])).status_code == 302
        return (b"v=spf1 -all",)
    assert domains.run_pending(workspace.pk, resolver=revoke_mid_request)
    with transaction.atomic():
        tenancy.set_workspace(workspace.pk)
        assert DomainJob.objects.first().status == "cancelled"
        assert DomainJob.objects.first().observations == []
        assert not Action.objects.get(source_kind="dns").current_gap
    settings.DNS_CHECKS_ENABLED = False
    assert client.post(detail_url, {"operation": "verify"}).status_code == 403
    assert not domains.run_pending(workspace.pk, resolver=lambda name: pytest.fail(name))


def test_dns_exact_name_and_limited_record_classification():
    assert normalize_domain(" BÜCHER.de. ") == "xn--bcher-kva.de"
    assert summarize("DMARC", (b"v=DMARC1; p=quarantine",))[0] == "present"
    assert summarize("DMARC", (b"v=DMARC1; p=none; p=reject",))[0] == "needs_review"
    assert "Inheritance is undetermined" in summarize("DMARC", ())[1]
    assert summarize("SPF", None)[0] == "inconclusive"


def test_runtime_role_cannot_read_unscoped_assessments_or_mutate_reports(workspace_factory):
    workspace, owner = workspace_factory("Alpha", "owner@alpha.example")
    submit(workspace, owner, prepare_assessment(workspace, owner, answers_with()))
    db = connection.settings_dict
    with psycopg.connect(
        host=db["HOST"], port=db["PORT"], dbname=db["NAME"], user=settings.DB_APP_ROLE, password="aegis_app_dev",
    ) as conn, conn.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM posture_assessment")
        assert cursor.fetchone() == (0,)
        cursor.execute("SELECT set_config('app.workspace_id', %s, true)", [str(workspace.pk)])
        cursor.execute("SELECT count(*) FROM posture_assessment")
        assert cursor.fetchone() == (1,)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            cursor.execute("UPDATE posture_report SET snapshot = '{}'::jsonb")
        conn.rollback()
