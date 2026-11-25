# Contributing to AegisOne Open

Thank you for helping build accessible, self-hostable security and audit infrastructure for small businesses, NGOs, and community organizations.

## Development Setup

Prerequisites: Docker, [uv](https://docs.astral.sh/uv/), and Python 3.13.

```bash
docker compose up -d db
uv sync
DJANGO_DEBUG=1 DJANGO_DB_ROLE=owner uv run python manage.py migrate
uv run pytest
```

## Contribution Guidelines

1. **Preserve security boundaries:** Every tenant-scoped model must enforce PostgreSQL `FORCE ROW LEVEL SECURITY` and include cross-workspace negative tests under the unprivileged `aegis_app` runtime role.
2. **Zero third-party frontend trackers or proprietary bundles:** All scripts and styles must pass the strict `'self'` Content Security Policy (`apps/core/middleware.py`) and use OSI-approved open-source licenses compatible with `Apache-2.0`.
3. **Plain-English guidance:** Assessment prompts and remediation steps (`apps/posture/catalog.py`) should remain actionable for small organizations without dedicated security teams. Version the catalog whenever scoring or questions change.
4. **Verification before pull requests:**
   - `uv run pytest -q`
   - `DJANGO_DEBUG=1 uv run python manage.py makemigrations --check --dry-run`

## License

By submitting a contribution to this repository, you agree that your contribution is licensed under the [Apache License, Version 2.0](LICENSE).
