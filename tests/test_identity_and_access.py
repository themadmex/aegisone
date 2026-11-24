"""V01 identity and roles, V08 direct-request authorisation."""

import re
import threading
from datetime import timedelta

import pytest
from django.core import mail
from django.db import connection, transaction
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AccountToken
from apps.core import tenancy, tokens
from apps.workspaces import services
from apps.workspaces.models import Invitation, Membership

from .conftest import add_member, make_user, sign_in_verified

pytestmark = pytest.mark.django_db(transaction=True)


def _invite_token_from_mail():
    body = mail.outbox[-1].body
    return re.search(r"/invite/([A-Za-z0-9_\-]+)", body).group(1)


# --- Sign-in and MFA ------------------------------------------------------------


def test_sign_in_requires_mfa_before_any_workspace_page(client, workspace_factory):
    workspace_factory("Alpha Ltd", "owner@alpha.example")
    resp = client.post(reverse("accounts:sign_in"), {"email": "OWNER@alpha.example", "password": "correct horse battery staple"})
    assert resp.status_code == 302 and resp["Location"] == reverse("accounts:mfa")
    resp = client.get(reverse("workspaces:overview"))
    assert resp.status_code == 302 and resp["Location"] == reverse("accounts:mfa")


def test_wrong_password_gives_generic_message(client, workspace_factory):
    workspace_factory("Alpha Ltd", "owner@alpha.example")
    for email in ("owner@alpha.example", "nobody@alpha.example"):
        resp = client.post(reverse("accounts:sign_in"), {"email": email, "password": "wrong password here"})
        assert resp.status_code == 400
        assert "don’t match" in resp.content.decode()


def test_mfa_enrolment_issues_recovery_codes_and_verifies(client, workspace_factory):
    _, owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    client.force_login(owner)
    resp = client.get(reverse("accounts:mfa"))
    assert resp.status_code == 200 and b"<svg" in resp.content
    from django_otp.oath import TOTP
    from django_otp.plugins.otp_totp.models import TOTPDevice

    device = TOTPDevice.objects.get(user=owner, confirmed=False)
    code = f"{TOTP(device.bin_key, device.step, device.t0, device.digits).token():06d}"
    resp = client.post(reverse("accounts:mfa"), {"code": code})
    assert resp.status_code == 200
    assert len(re.findall(r"<li>[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}</li>", resp.content.decode())) == 10
    assert client.get(reverse("workspaces:overview")).status_code == 200


def test_recovery_code_works_once(client, workspace_factory):
    from apps.accounts import mfa

    _, owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    sign_in_verified(client, owner)
    codes = mfa.issue_recovery_codes(owner)
    client.logout()
    for expected in (302, 400):
        client.force_login(owner)
        resp = client.post(reverse("accounts:mfa"), {"code": codes[0]})
        assert resp.status_code == expected
        client.logout()


# --- Profile settings -----------------------------------------------------------


def test_profile_is_mfa_gated_and_updates_only_the_signed_in_user(client, workspace_factory):
    _, owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    other = make_user("other@alpha.example", name="Other user")
    url = reverse("accounts:profile")
    assert client.get(url)["Location"].startswith(reverse("accounts:sign_in"))
    client.force_login(owner)
    assert client.post(url, {"name": "Too soon"})["Location"] == reverse("accounts:mfa")

    sign_in_verified(client, owner)
    assert client.get(url).status_code == 200
    response = client.post(url, {"name": "Updated name", "user_id": other.pk, "email": other.email}, follow=True)
    assert response.status_code == 200 and b"Profile saved." in response.content
    owner.refresh_from_db()
    other.refresh_from_db()
    assert (owner.name, owner.email, other.name) == ("Updated name", "owner@alpha.example", "Other user")


def test_profile_password_change_requires_current_password_and_revokes_sessions(client, workspace_factory):
    _, owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    sign_in_verified(client, owner)
    other_session = sign_in_verified(client.__class__(), owner)
    token = AccountToken.objects.create(
        user=owner, purpose=AccountToken.PURPOSE_RECOVERY, digest=tokens.digest("old-recovery-link"),
        expires_at=timezone.now() + timedelta(minutes=15),
    )
    url = reverse("accounts:change_password")
    data = {
        "old_password": "not the current password",
        "new_password1": "new passphrase for testing",
        "new_password2": "new passphrase for testing",
    }
    assert client.post(url, data).context["password_form"]["old_password"].errors

    data["old_password"] = "correct horse battery staple"
    response = client.post(url, data)
    assert response["Location"] == reverse("accounts:sign_in") + "?reset=1"
    owner.refresh_from_db()
    token.refresh_from_db()
    assert owner.check_password(data["new_password1"])
    assert token.consumed_at is not None
    for session in (client, other_session):
        assert session.get(reverse("accounts:profile"))["Location"].startswith(reverse("accounts:sign_in"))


def test_recovery_mail_failure_keeps_the_generic_response(client, workspace_factory, monkeypatch):
    _, owner = workspace_factory("Alpha Ltd", "owner@alpha.example")

    def unavailable(**kwargs):
        raise TimeoutError

    monkeypatch.setattr("apps.accounts.views.send_mail", unavailable)
    url = reverse("accounts:recovery")
    failed = client.post(url, {"email": owner.email})
    unknown = client.post(url, {"email": "unknown@alpha.example"})
    assert failed.status_code == unknown.status_code == 200
    assert failed.templates[0].name == unknown.templates[0].name == "accounts/recovery_sent.html"
    assert not AccountToken.objects.filter(user=owner).exists()


# --- Invitations ----------------------------------------------------------------


def test_owner_invite_flow_creates_contributor(client, workspace_factory):
    workspace, owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    sign_in_verified(client, owner)
    resp = client.post(reverse("workspaces:invite"), {"email": "Tunde@Alpha.example"})
    assert resp.status_code == 302
    token = _invite_token_from_mail()
    client.logout()

    resp = client.post(reverse("accounts:accept_invite", args=[token]), {"name": "Tunde", "password": "a long enough phrase 42"})
    assert resp.status_code == 302 and resp["Location"] == reverse("accounts:mfa")
    with transaction.atomic():
        tenancy.set_workspace(workspace.id)
        m = Membership.objects.get(user__email="tunde@alpha.example")
        assert m.role == Membership.CONTRIBUTOR


def test_invite_link_is_single_use(client, workspace_factory):
    workspace, owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    with transaction.atomic():
        tenancy.set_workspace(workspace.id)
        raw = services.invite(workspace, "new@alpha.example", "contributor", owner)
    data = {"name": "New", "password": "a long enough phrase 42"}
    assert client.post(reverse("accounts:accept_invite", args=[raw]), data).status_code == 302
    client.logout()
    assert client.get(reverse("accounts:accept_invite", args=[raw])).status_code == 410


def test_concurrent_redemption_accepts_exactly_one(workspace_factory):
    workspace, owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    with transaction.atomic():
        tenancy.set_workspace(workspace.id)
        raw = services.invite(workspace, "race@alpha.example", "contributor", owner)
    user = make_user("race@alpha.example")
    results, barrier = [], threading.Barrier(2)

    def redeem():
        try:
            barrier.wait()
            with transaction.atomic():
                inv = services.find_invitation(raw)
                services.accept(inv, user)
            results.append("ok")
        except services.InvitationUnavailable:
            results.append("refused")
        finally:
            connection.close()

    threads = [threading.Thread(target=redeem) for _ in range(2)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results) == ["ok", "refused"]


def test_resend_retires_the_old_link(client, workspace_factory):
    workspace, owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    sign_in_verified(client, owner)
    client.post(reverse("workspaces:invite"), {"email": "ngozi@alpha.example"})
    old = _invite_token_from_mail()
    with transaction.atomic():
        tenancy.set_workspace(workspace.id)
        inv = Invitation.objects.get(token_digest=tokens.digest(old))
    client.post(reverse("workspaces:resend_invite", args=[inv.id]))
    new = _invite_token_from_mail()
    assert new != old
    client.logout()
    assert client.get(reverse("accounts:accept_invite", args=[old])).status_code == 410
    assert client.get(reverse("accounts:accept_invite", args=[new])).status_code == 200


def test_expired_invite_is_refused(client, workspace_factory):
    workspace, owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    with transaction.atomic():
        tenancy.set_workspace(workspace.id)
        raw = services.invite(workspace, "late@alpha.example", "contributor", owner)
        Invitation.objects.filter(email="late@alpha.example").update(expires_at=timezone.now())
    assert client.get(reverse("accounts:accept_invite", args=[raw])).status_code == 410


def test_invite_for_another_address_is_refused_when_signed_in(client, workspace_factory):
    workspace, owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    with transaction.atomic():
        tenancy.set_workspace(workspace.id)
        raw = services.invite(workspace, "someone@alpha.example", "contributor", owner)
    sign_in_verified(client, owner)
    resp = client.post(reverse("accounts:accept_invite", args=[raw]))
    assert resp.status_code == 409


def test_invalid_invite_email_shows_error(client, workspace_factory):
    _, owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    sign_in_verified(client, owner)
    resp = client.post(reverse("workspaces:invite"), {"email": "ngozi@"})
    assert resp.status_code == 400
    assert "Enter a full email address" in resp.content.decode()


# --- Roles and removal ----------------------------------------------------------


def test_contributor_cannot_manage_members(client, workspace_factory):
    workspace, _ = workspace_factory("Alpha Ltd", "owner@alpha.example")
    contributor = make_user("c@alpha.example")
    add_member(workspace, contributor, Membership.CONTRIBUTOR)
    sign_in_verified(client, contributor)
    assert client.get(reverse("workspaces:members")).status_code == 403
    assert client.post(reverse("workspaces:invite"), {"email": "x@alpha.example"}).status_code == 403


def test_removed_member_loses_access_on_next_request(client, workspace_factory):
    workspace, owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    member = make_user("m@alpha.example")
    m = add_member(workspace, member, Membership.CONTRIBUTOR)
    sign_in_verified(client, member)
    assert client.get(reverse("workspaces:overview")).status_code == 200
    with transaction.atomic():
        tenancy.set_workspace(workspace.id)
        services.remove_member(workspace, m.id, owner)
    resp = client.get(reverse("workspaces:overview"))
    assert resp.status_code == 403
    assert b"don\xe2\x80\x99t have access" in resp.content


def test_last_owner_cannot_be_removed(workspace_factory):
    workspace, owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    with transaction.atomic():
        tenancy.set_workspace(workspace.id)
        m = Membership.objects.get(user=owner)
        with pytest.raises(services.LastOwnerError):
            services.remove_member(workspace, m.id, owner)


def test_owner_cannot_remove_a_member_of_another_workspace(client, workspace_factory):
    _, alpha_owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    beta, _ = workspace_factory("Beta Ltd", "owner@beta.example")
    victim = make_user("v@beta.example")
    vm = add_member(beta, victim, Membership.CONTRIBUTOR)
    sign_in_verified(client, alpha_owner)
    assert client.post(reverse("workspaces:remove_member", args=[vm.id])).status_code == 404
    with transaction.atomic():
        tenancy.set_workspace(beta.id)
        assert Membership.objects.get(pk=vm.pk).revoked_at is None


def test_switching_to_a_foreign_workspace_is_refused(client, workspace_factory):
    _, alpha_owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    beta, _ = workspace_factory("Beta Ltd", "owner@beta.example")
    sign_in_verified(client, alpha_owner)
    assert client.post(reverse("workspaces:switch"), {"workspace_id": str(beta.id)}).status_code == 404


# --- Sessions and recovery ------------------------------------------------------


def test_password_reset_ends_existing_sessions(client, workspace_factory):
    _, owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    sign_in_verified(client, owner)
    assert client.get(reverse("workspaces:overview")).status_code == 200

    other = client.__class__()
    other.post(reverse("accounts:recovery"), {"email": "owner@alpha.example"})
    raw = re.search(r"/recovery/([A-Za-z0-9_\-]+)", mail.outbox[-1].body).group(1)
    resp = other.post(reverse("accounts:recovery_confirm", args=[raw]), {"password": "a brand new long phrase 7"})
    assert resp.status_code == 302

    # The old session is signed out (Django's password-hash check fires first).
    resp = client.get(reverse("workspaces:overview"))
    assert resp.status_code == 302 and resp["Location"].startswith(reverse("accounts:sign_in"))
    assert other.get(reverse("accounts:recovery_confirm", args=[raw])).status_code == 410


def test_revoking_sessions_signs_out_every_device(client, workspace_factory):
    _, owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    sign_in_verified(client, owner)
    assert client.get(reverse("workspaces:overview")).status_code == 200
    owner.end_all_sessions()
    resp = client.get(reverse("workspaces:overview"))
    assert resp.status_code == 302 and "ended=1" in resp["Location"]


def test_recovery_request_does_not_reveal_accounts(client, workspace_factory):
    workspace_factory("Alpha Ltd", "owner@alpha.example")
    a = client.post(reverse("accounts:recovery"), {"email": "owner@alpha.example"})
    b = client.post(reverse("accounts:recovery"), {"email": "nobody@alpha.example"})
    assert a.status_code == b.status_code == 200
    assert a.content == b.content


def test_session_has_an_absolute_lifetime(client, workspace_factory, settings):
    _, owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    sign_in_verified(client, owner)
    session = client.session
    session["aegis_auth_at"] = timezone.now().timestamp() - settings.SESSION_ABSOLUTE_LIFETIME.total_seconds() - 1
    session.save()
    resp = client.get(reverse("workspaces:overview"))
    assert resp.status_code == 302 and "ended=1" in resp["Location"]


# --- Response hardening ---------------------------------------------------------


def test_private_pages_are_no_store_and_have_csp(client, workspace_factory):
    _, owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    sign_in_verified(client, owner)
    resp = client.get(reverse("workspaces:overview"))
    assert resp["Cache-Control"] == "no-store"
    assert "default-src 'self'" in resp["Content-Security-Policy"]
    assert resp["X-Frame-Options"] == "DENY"


def test_admin_is_not_mounted(client):
    assert client.get("/admin/").status_code == 404
