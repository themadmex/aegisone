from importlib import import_module

from django.db import migrations

ROLE = import_module("apps.posture.migrations.0002_security").ROLE


class Migration(migrations.Migration):
    dependencies = [("posture", "0005_exportpayload_and_more")]
    operations = [migrations.RunSQL(
        f"""
ALTER TABLE posture_exportpayload ENABLE ROW LEVEL SECURITY;
ALTER TABLE posture_exportpayload FORCE ROW LEVEL SECURITY;
CREATE POLICY workspace_scope ON posture_exportpayload
    USING (workspace_id = app_current_workspace_id())
    WITH CHECK (workspace_id = app_current_workspace_id());
ALTER TABLE posture_exportpayload ADD CONSTRAINT export_same_workspace
    FOREIGN KEY (workspace_id, request_id) REFERENCES posture_datarequest (workspace_id, id);
REVOKE ALL ON posture_exportpayload FROM {ROLE};
GRANT SELECT ON posture_exportpayload TO {ROLE};
""",
        f"""
REVOKE ALL ON posture_exportpayload FROM {ROLE};
ALTER TABLE posture_exportpayload DROP CONSTRAINT export_same_workspace;
DROP POLICY workspace_scope ON posture_exportpayload;
ALTER TABLE posture_exportpayload NO FORCE ROW LEVEL SECURITY;
ALTER TABLE posture_exportpayload DISABLE ROW LEVEL SECURITY;
""",
    )]
