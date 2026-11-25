# AegisOne Open

Plain-English security self-assessment and shared audit infrastructure for small businesses, NGOs, and community organizations—turning everyday security checks into a ranked action plan and a dated, verifiable report. Open source under [Apache-2.0](LICENSE) and self-hostable.

**Status:** invite-only pilot development. The local build supports assessments, actions, reports, approved workspace exports and closure, and optional DNS observations. General release remains **NO-GO**. See the [slice audit and verification record](docs/production-readiness/16-slice-audit-and-verification.md), [security policy](SECURITY.md), and [contributing guide](CONTRIBUTING.md).

## What's here

| Path | Contents |
|---|---|
| `docs/production-readiness/` | Planning pack: PRD, TRD, UI/UX, flows, schema, threat model, tests, release gates |
| `design/canvas/` | Approved screen designs (open the canvas link in the docs or the `.dc.html` files) |
| `apps/accounts/` | Users, sign-in, two-step sign-in (TOTP + recovery codes), password recovery, invite acceptance |
| `apps/workspaces/` | Workspaces, memberships, invitations, owner/contributor roles |
| `apps/core/` | Tenant context, audit log, session policy, security headers |
| `apps/posture/` | Versioned assessment, prioritized actions, private reports, data requests, and optional DNS jobs |
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

### Browser verification

Use a disposable local database and application. The browser test creates synthetic workspaces and completes invitation, MFA, assessment, actions, print, data request, and profile flows. It requires Edge and Chrome plus `playwright-core` and `@axe-core/playwright` installed in your Node module search path. Set `AEGIS_BROWSER_URL` to the local application's origin, `AEGIS_BROWSER_DB_PORT` to the local PostgreSQL port, and optionally `AEGIS_BROWSER_EVIDENCE` to a local output directory. Run `node tests/browser_smoke.cjs`. The script defaults to the isolated ports 58042 and 55492.

## Pilot user guide

1. Open your invitation, create your account, enroll an authenticator and store your recovery codes privately.
2. Open **Assessment** and save each answer as you continue. Return to Assessment to resume. Review all 21 answers, then submit the dated self-reported baseline.
3. Open **Actions** to see the highest-priority gaps, how to address each one and how to confirm the fix. Select a status as you work. A new assessment can reopen a completed item if the gap is reported again.
4. Open **Reports**, preview the current evidence, then save a private snapshot. Use **Print or save as PDF** for a local copy. The creator or an owner can revoke access to a saved report.
5. Open the avatar menu for **Profile settings**. Owners can manage members and open **Data and privacy** to request an export or closure. An operator verifies the request before processing it. A completed export is available to the requesting owner for seven days.
6. When **Domains** is enabled, owners can attest authorization, publish the exact TXT proof and queue an SPF/DMARC observation. Return to the domain page for its status. Domain checks cover the exact name, and observations do not determine mail delivery or enforcement.

## Self-host operations

Compose is for local evaluation with synthetic data and fixed development credentials. For a hosted install use a private PostgreSQL instance, separate runtime and migration roles, a strong signing secret, equivalent TLS proxy settings and your own secret store. Supply authenticated SMTP settings from `.env.example`. Run `manage.py migrate --noinput` under `DJANGO_DB_ROLE=owner` before starting the new web image. Keep the previous compatible image and schema backup available for rollback.

Keep `DNS_CHECKS_ENABLED=0` until the deployment has a restricted worker, approved resolver egress, alerting and a validated test zone. The batch entry point is `manage.py process_dns_job --workspace <workspace-uuid>`. A scheduler may run it for an explicitly enrolled workspace. It performs at most one authorized job per invocation and uses the same application configuration as the web service.

For data requests, verify the owner's identity and authority out of band and document the operator decision. Use the migration/operator database identity to run `manage.py review_data_request --workspace <uuid> --request <uuid> --verified-owner <email> --decision review|export|closure|decline`. Closure suspends workspace access. `manage.py prune_workspace_artifacts --workspace <uuid>` previews scoped expiry cleanup. Run it with `--apply` only under the approved retention schedule. Tenant deletion reconciliation and production restore need an approved operational runbook.

## How tenant isolation works

- The web process connects as `aegis_app`, which owns no tables and has no `BYPASSRLS`.
- Every request runs in a single transaction. After the server checks the user's current membership, it sets `app.workspace_id` with `SET LOCAL`.
- PostgreSQL policies on every tenant table only return rows for that workspace. With no context set, nothing is visible.
- Users can see their own memberships so they can switch workspaces. An invite token exposes only its own invitation.
