# AegisOne Open

A plain-English security self-assessment for small businesses that turns answers into a ranked action plan and a dated report. Open source (Apache-2.0, pending founder confirmation) and self-hostable.

**Status:** pre-pilot development. Build slice S1 (workspaces and identity) is in progress. Production verdict: **NO-GO** (see `docs/production-readiness/12-release-readiness.md`).

## What's here

| Path | Contents |
|---|---|
| `docs/production-readiness/` | Planning pack: PRD, TRD, UI/UX, flows, schema, threat model, tests, release gates |
| `design/canvas/` | Approved screen designs (open the canvas link in the docs or the `.dc.html` files) |
| `apps/accounts/` | Users, sign-in, two-step sign-in (TOTP + recovery codes), password recovery, invite acceptance |
| `apps/workspaces/` | Workspaces, memberships, invitations, owner/contributor roles |
| `apps/core/` | Tenant context, audit log, session policy, security headers |
| `tests/` | PostgreSQL integration tests, including row-level security under the real runtime role |

## Run it locally

Requires Docker, [uv](https://docs.astral.sh/uv/) and Python 3.13.

```bash
docker compose up -d db                      # PostgreSQL 17 with the owner and runtime roles
uv sync
DJANGO_DEBUG=1 DJANGO_DB_ROLE=owner uv run python manage.py migrate
DJANGO_DEBUG=1 uv run python manage.py provision_workspace --name "Sample Co." --owner-email you@example.com
DJANGO_DEBUG=1 uv run python manage.py runserver
```

The owner invite link prints to the console (development email backend). Open it, create your account and set up an authenticator app.

Or run everything in containers: `docker compose up --build`, then open http://localhost:8000.

## Tests

```bash
docker compose up -d db
uv run pytest
```

Tests run against real PostgreSQL. They use the schema-owning role, which is still subject to `FORCE ROW LEVEL SECURITY`. One test connects as the runtime role to prove it can't bypass row security or rewrite the audit log.

## How tenant isolation works

- The web process connects as `aegis_app`, which owns no tables and has no `BYPASSRLS`.
- Every request runs in a single transaction. After the server checks the user's current membership, it sets `app.workspace_id` with `SET LOCAL`.
- PostgreSQL policies on every tenant table only return rows for that workspace. With no context set, nothing is visible.
- Users can see their own memberships so they can switch workspaces. An invite token exposes only its own invitation.
