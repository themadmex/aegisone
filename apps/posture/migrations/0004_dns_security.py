from importlib import import_module

from django.db import migrations

ROLE = import_module("apps.posture.migrations.0002_security").ROLE
TENANT_TABLES = ("posture_domain", "posture_domainjob")
GLOBAL_TABLES = ("posture_dnspermit", "posture_dnscooldown")
POLICIES = "\n".join(
    f"""ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
CREATE POLICY workspace_scope ON {table}
    USING (workspace_id = app_current_workspace_id())
    WITH CHECK (workspace_id = app_current_workspace_id());"""
    for table in TENANT_TABLES
)
REVOKE = "\n".join(f"REVOKE ALL ON {table} FROM {ROLE};" for table in TENANT_TABLES + GLOBAL_TABLES)
GRANT = "\n".join(f"GRANT SELECT, INSERT, UPDATE ON {table} TO {ROLE};" for table in TENANT_TABLES + GLOBAL_TABLES)
REVERSE_POLICIES = "\n".join(
    f"DROP POLICY workspace_scope ON {table}; ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY; "
    f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;" for table in TENANT_TABLES
)


class Migration(migrations.Migration):
    dependencies = [("posture", "0003_dnscooldown_dnspermit_domain_domainjob_and_more")]
    operations = [migrations.RunSQL(
        POLICIES + REVOKE + GRANT + """
ALTER TABLE posture_domainjob ADD CONSTRAINT domain_job_same_workspace
    FOREIGN KEY (workspace_id, domain_id) REFERENCES posture_domain (workspace_id, id);
""",
        "ALTER TABLE posture_domainjob DROP CONSTRAINT domain_job_same_workspace;" + REVOKE + REVERSE_POLICIES,
    )]
