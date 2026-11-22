"""Transaction-local tenant context for PostgreSQL row-level security.

Every policy reads these settings through the app_current_* SQL functions
created in the workspaces security migration. Values are set with
set_config(..., is_local => true), so they vanish when the transaction ends and
cannot leak to the next request on a pooled connection. Outside a transaction
there is no context at all, and policies return no rows.
"""

from django.db import connection


class TenantContextError(RuntimeError):
    pass


def _set(name, value):
    if not connection.in_atomic_block:
        raise TenantContextError("Tenant context must be set inside a transaction")
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config(%s, %s, true)", [name, "" if value is None else str(value)])


def set_user(user_id):
    """Allow the current user to see their own memberships (workspace switcher)."""
    _set("app.user_id", user_id)


def set_workspace(workspace_id):
    """Scope all tenant tables to one workspace the server has already authorised."""
    _set("app.workspace_id", workspace_id)


def set_invite_digest(digest):
    """Expose only the single invitation whose token digest matches."""
    _set("app.invite_digest", digest)


def clear():
    for name in ("app.user_id", "app.workspace_id", "app.invite_digest"):
        _set(name, None)
