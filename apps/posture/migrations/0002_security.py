import re

from django.conf import settings
from django.db import migrations

ROLE = settings.DB_APP_ROLE
if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", ROLE):
    raise ValueError("DB_APP_ROLE must be a lower-case PostgreSQL identifier")

TABLES = ("posture_assessment", "posture_action", "posture_actionevent", "posture_report", "posture_datarequest")
POLICIES = "\n".join(
    f"""ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
CREATE POLICY workspace_scope ON {table}
    USING (workspace_id = app_current_workspace_id())
    WITH CHECK (workspace_id = app_current_workspace_id());
REVOKE ALL ON {table} FROM {ROLE};
GRANT SELECT, INSERT ON {table} TO {ROLE};"""
    for table in TABLES
)
REVERSE_POLICIES = "\n".join(
    f"""DROP POLICY workspace_scope ON {table};
ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;
ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
REVOKE ALL ON {table} FROM {ROLE};"""
    for table in TABLES
)


class Migration(migrations.Migration):
    dependencies = [("posture", "0001_initial"), ("workspaces", "0002_row_level_security")]
    operations = [migrations.RunSQL(
        POLICIES + f"""
GRANT UPDATE ON posture_assessment, posture_action TO {ROLE};
GRANT UPDATE (revoked_at) ON posture_report TO {ROLE};
ALTER TABLE posture_actionevent ADD CONSTRAINT event_same_workspace
    FOREIGN KEY (workspace_id, action_id) REFERENCES posture_action (workspace_id, id);

CREATE FUNCTION posture_preserve_submission() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.submitted_at IS NOT NULL THEN
        RAISE EXCEPTION 'Submitted assessments are immutable' USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER preserve_submission BEFORE UPDATE ON posture_assessment
    FOR EACH ROW EXECUTE FUNCTION posture_preserve_submission();

CREATE FUNCTION posture_preserve_report() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (to_jsonb(OLD) - 'revoked_at') IS DISTINCT FROM (to_jsonb(NEW) - 'revoked_at')
       OR OLD.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'Saved report content is immutable' USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER preserve_report BEFORE UPDATE ON posture_report
    FOR EACH ROW EXECUTE FUNCTION posture_preserve_report();
""",
        """
DROP TRIGGER preserve_report ON posture_report;
DROP FUNCTION posture_preserve_report();
DROP TRIGGER preserve_submission ON posture_assessment;
DROP FUNCTION posture_preserve_submission();
ALTER TABLE posture_actionevent DROP CONSTRAINT event_same_workspace;
""" + REVERSE_POLICIES,
    )]
