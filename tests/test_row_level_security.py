"""V08: tenant isolation is enforced by PostgreSQL, not only by application code."""

import psycopg
import pytest
from django.conf import settings
from django.db import connection, transaction

from apps.core import tenancy
from apps.core.models import AuditEvent
from apps.workspaces.models import Invitation, Membership, Workspace

from .conftest import add_member, make_user

# Real transactions, not the default wrapping transaction: set_config(..., true)
# lasts until the outermost transaction ends, so only real transactions prove
# that context does not leak from one unit of work to the next.
pytestmark = pytest.mark.django_db(transaction=True)


def test_unset_context_sees_no_tenant_rows(workspace_factory):
    workspace_factory("Alpha Ltd", "owner@alpha.example")
    with transaction.atomic():
        assert Workspace.objects.count() == 0
        assert Membership.objects.count() == 0
        assert Invitation.objects.count() == 0


def test_workspace_context_only_shows_that_workspace(workspace_factory):
    alpha, _ = workspace_factory("Alpha Ltd", "owner@alpha.example")
    beta, _ = workspace_factory("Beta Ltd", "owner@beta.example")
    with transaction.atomic():
        tenancy.set_workspace(alpha.id)
        assert list(Workspace.objects.values_list("name", flat=True)) == ["Alpha Ltd"]
        assert set(Membership.objects.values_list("workspace_id", flat=True)) == {alpha.id}
        assert set(Invitation.objects.values_list("workspace_id", flat=True)) == {alpha.id}
        assert not Membership.objects.filter(workspace=beta).exists()


def test_cannot_write_into_another_workspace(workspace_factory):
    alpha, _ = workspace_factory("Alpha Ltd", "owner@alpha.example")
    beta, _ = workspace_factory("Beta Ltd", "owner@beta.example")
    intruder = make_user("intruder@alpha.example")
    with pytest.raises(Exception), transaction.atomic():
        tenancy.set_workspace(alpha.id)
        Membership.objects.create(workspace=beta, user=intruder, role=Membership.OWNER)


def test_cross_tenant_update_affects_nothing(workspace_factory):
    alpha, _ = workspace_factory("Alpha Ltd", "owner@alpha.example")
    beta, beta_owner = workspace_factory("Beta Ltd", "owner@beta.example")
    with transaction.atomic():
        tenancy.set_workspace(alpha.id)
        assert Membership.objects.filter(workspace_id=beta.id).update(role="contributor") == 0
    with transaction.atomic():
        tenancy.set_workspace(beta.id)
        assert Membership.objects.get(user=beta_owner).role == Membership.OWNER


def test_user_sees_own_memberships_but_not_colleagues_elsewhere(workspace_factory):
    alpha, alpha_owner = workspace_factory("Alpha Ltd", "owner@alpha.example")
    beta, beta_owner = workspace_factory("Beta Ltd", "owner@beta.example")
    add_member(beta, alpha_owner, Membership.CONTRIBUTOR)
    with transaction.atomic():
        tenancy.set_user(alpha_owner.id)
        visible = set(Membership.objects.values_list("workspace_id", "user_id"))
        assert visible == {(alpha.id, alpha_owner.id), (beta.id, alpha_owner.id)}
        assert (beta.id, beta_owner.id) not in visible
        assert set(Workspace.objects.values_list("name", flat=True)) == {"Alpha Ltd", "Beta Ltd"}


def test_revoked_membership_hides_the_workspace(workspace_factory):
    alpha, _ = workspace_factory("Alpha Ltd", "owner@alpha.example")
    member = make_user("member@alpha.example")
    m = add_member(alpha, member, Membership.CONTRIBUTOR)
    with transaction.atomic():
        tenancy.set_workspace(alpha.id)
        Membership.objects.filter(pk=m.pk).update(revoked_at="2026-11-22T00:00:00Z")
    with transaction.atomic():
        tenancy.set_user(member.id)
        assert Workspace.objects.count() == 0


def test_invite_digest_exposes_only_that_invitation(workspace_factory):
    alpha, _ = workspace_factory("Alpha Ltd", "owner@alpha.example")
    workspace_factory("Beta Ltd", "owner@beta.example")
    with transaction.atomic():
        tenancy.set_workspace(alpha.id)
        digest = Invitation.objects.first().token_digest
    with transaction.atomic():
        tenancy.set_invite_digest(digest)
        assert Invitation.objects.count() == 1
        assert list(Workspace.objects.values_list("name", flat=True)) == ["Alpha Ltd"]
        assert Membership.objects.count() == 0


def test_context_does_not_survive_the_transaction(workspace_factory):
    alpha, _ = workspace_factory("Alpha Ltd", "owner@alpha.example")
    with transaction.atomic():
        tenancy.set_workspace(alpha.id)
        assert Workspace.objects.count() == 1
    with transaction.atomic():
        assert Workspace.objects.count() == 0


def test_every_tenant_table_forces_row_level_security():
    """Guard for future slices: any table with workspace_id must enable and force RLS."""
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r'
              AND (c.relname = 'workspaces' OR EXISTS (
                SELECT 1 FROM pg_attribute a
                WHERE a.attrelid = c.oid AND a.attname = 'workspace_id' AND NOT a.attisdropped))
            """
        )
        rows = cur.fetchall()
    assert {r[0] for r in rows} >= {"workspaces", "memberships", "invitations", "audit_events"}
    unprotected = [name for name, enabled, forced in rows if not (enabled and forced)]
    assert unprotected == []


def test_setting_context_outside_a_transaction_is_refused():
    with pytest.raises(tenancy.TenantContextError):
        tenancy.set_workspace("00000000-0000-0000-0000-000000000000")


def test_runtime_role_cannot_bypass_rls_or_rewrite_audit(workspace_factory):
    """Connect as the real runtime role and check its privileges directly."""
    alpha, _ = workspace_factory("Alpha Ltd", "owner@alpha.example")
    db = connection.settings_dict
    with psycopg.connect(
        host=db["HOST"], port=db["PORT"], dbname=db["NAME"],
        user=settings.DB_APP_ROLE, password=_app_password(), autocommit=False,
    ) as conn, conn.cursor() as cur:
        cur.execute("SELECT rolbypassrls, rolsuper FROM pg_roles WHERE rolname = current_user")
        assert cur.fetchone() == (False, False)
        cur.execute("SELECT count(*) FROM workspaces")
        assert cur.fetchone()[0] == 0, "runtime role must see nothing without context"
        cur.execute("SELECT set_config('app.workspace_id', %s, true)", [str(alpha.id)])
        cur.execute("SELECT count(*) FROM audit_events")
        assert cur.fetchone()[0] >= 1
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            cur.execute("UPDATE audit_events SET outcome = 'failure'")
        conn.rollback()
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            cur.execute("ALTER TABLE workspaces DISABLE ROW LEVEL SECURITY")
        conn.rollback()
    assert AuditEvent.objects is not None


def _app_password():
    import os

    return os.environ.get("DB_PASSWORD", "aegis_app_dev")
