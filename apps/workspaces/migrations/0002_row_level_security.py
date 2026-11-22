"""Row-level security for every tenant table, plus runtime-role grants.

Policies read transaction-local settings (see apps.core.tenancy). An unset
setting is NULL, every comparison with NULL is false, and so a request without
authorised context sees and writes nothing. FORCE makes the policies apply to
the table owner too; only superusers and BYPASSRLS roles skip them, and the
application never uses either.
"""

import re

from django.conf import settings
from django.db import migrations

APP_ROLE = settings.DB_APP_ROLE
if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", APP_ROLE):
    raise ValueError("DB_APP_ROLE must be a plain lower-case PostgreSQL identifier")

TENANT_TABLES = ["workspaces", "memberships", "invitations", "audit_events"]

FORWARD = f"""
CREATE OR REPLACE FUNCTION app_current_user_id() RETURNS uuid
  LANGUAGE sql STABLE AS $$ SELECT NULLIF(current_setting('app.user_id', true), '')::uuid $$;
CREATE OR REPLACE FUNCTION app_current_workspace_id() RETURNS uuid
  LANGUAGE sql STABLE AS $$ SELECT NULLIF(current_setting('app.workspace_id', true), '')::uuid $$;
CREATE OR REPLACE FUNCTION app_invite_digest() RETURNS text
  LANGUAGE sql STABLE AS $$ SELECT NULLIF(current_setting('app.invite_digest', true), '') $$;

{"".join(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY; ALTER TABLE {t} FORCE ROW LEVEL SECURITY;" for t in TENANT_TABLES)}

-- Workspaces: the authorised current workspace; read-only visibility of
-- workspaces where the current user has an active membership (switcher) or
-- that the presented invitation belongs to.
CREATE POLICY workspaces_current ON workspaces
  USING (id = app_current_workspace_id()) WITH CHECK (id = app_current_workspace_id());
CREATE POLICY workspaces_member_read ON workspaces FOR SELECT
  USING (id IN (SELECT workspace_id FROM memberships
                WHERE user_id = app_current_user_id() AND revoked_at IS NULL));
CREATE POLICY workspaces_invite_read ON workspaces FOR SELECT
  USING (id IN (SELECT workspace_id FROM invitations WHERE token_digest = app_invite_digest()));

-- Memberships: everything in the current workspace; your own rows anywhere.
CREATE POLICY memberships_current ON memberships
  USING (workspace_id = app_current_workspace_id()) WITH CHECK (workspace_id = app_current_workspace_id());
CREATE POLICY memberships_self_read ON memberships FOR SELECT
  USING (user_id = app_current_user_id());

-- Invitations: the current workspace, or exactly the one matching the token.
CREATE POLICY invitations_current ON invitations
  USING (workspace_id = app_current_workspace_id()) WITH CHECK (workspace_id = app_current_workspace_id());
CREATE POLICY invitations_token_read ON invitations FOR SELECT
  USING (token_digest = app_invite_digest());

-- Audit: workspace events in the current workspace; account events are
-- written without a workspace and readable only by their actor.
CREATE POLICY audit_current ON audit_events
  USING (workspace_id = app_current_workspace_id()) WITH CHECK (workspace_id = app_current_workspace_id());
CREATE POLICY audit_account_insert ON audit_events FOR INSERT
  WITH CHECK (workspace_id IS NULL);
CREATE POLICY audit_account_read ON audit_events FOR SELECT
  USING (workspace_id IS NULL AND actor_id = app_current_user_id());

-- Runtime role: data access only. It owns nothing, so it cannot alter or
-- disable policies, and audit is append-only for it.
GRANT USAGE ON SCHEMA public TO {APP_ROLE};
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {APP_ROLE};
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE};
REVOKE UPDATE, DELETE, TRUNCATE ON audit_events FROM {APP_ROLE};
REVOKE TRUNCATE ON ALL TABLES IN SCHEMA public FROM {APP_ROLE};
GRANT EXECUTE ON FUNCTION app_current_user_id(), app_current_workspace_id(), app_invite_digest() TO {APP_ROLE};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_ROLE};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {APP_ROLE};
"""

REVERSE = f"""
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM {APP_ROLE};
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE, SELECT ON SEQUENCES FROM {APP_ROLE};
{"".join(f"DROP POLICY IF EXISTS {p} ON {t};" for t, p in [
    ("workspaces", "workspaces_current"), ("workspaces", "workspaces_member_read"),
    ("workspaces", "workspaces_invite_read"), ("memberships", "memberships_current"),
    ("memberships", "memberships_self_read"), ("invitations", "invitations_current"),
    ("invitations", "invitations_token_read"), ("audit_events", "audit_current"),
    ("audit_events", "audit_account_insert"), ("audit_events", "audit_account_read"),
])}
{"".join(f"ALTER TABLE {t} NO FORCE ROW LEVEL SECURITY; ALTER TABLE {t} DISABLE ROW LEVEL SECURITY;" for t in TENANT_TABLES)}
DROP FUNCTION IF EXISTS app_current_user_id();
DROP FUNCTION IF EXISTS app_current_workspace_id();
DROP FUNCTION IF EXISTS app_invite_digest();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("workspaces", "0001_initial"),
        ("core", "0001_initial"),
        ("accounts", "0001_initial"),
        ("sessions", "0001_initial"),
        ("otp_totp", "0003_add_timestamps"),
        ("otp_static", "0003_add_timestamps"),
    ]

    operations = [migrations.RunSQL(FORWARD, REVERSE)]
