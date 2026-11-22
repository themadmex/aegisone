from .models import AuditEvent


def record(action, *, actor=None, workspace=None, outcome="success", target=None):
    """Write an audit event inside the caller's transaction and tenant context."""
    AuditEvent.objects.create(
        action=action,
        actor=actor if getattr(actor, "is_authenticated", False) or actor is None else None,
        workspace=workspace,
        outcome=outcome,
        target_ref=str(target or "")[:64],
    )
