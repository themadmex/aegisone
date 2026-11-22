# Threat model, privacy and abuse

## Assets and boundaries

Restricted assets are account identity and factors, membership, assessment answers, action evidence, domain scope, reports, rights requests and backups. Actors include invited users, former members, malicious tenants, compromised operators, unauthenticated callers and untrusted external responses. Boundaries are browser to web, web to private database, worker lease to scoped database access, worker to approved resolver/relay, and deployment/backup control plane. Treat browser data, stale forms, DNS content and third-party mail outcomes as untrusted.

| Risk | Impact | Preventive controls and verification | Owner |
|---|---|---|---|
| T1 · Workspace leakage through API, jobs, reports, shared links or caches | High | Check current role on every request, forced RLS and composite keys, no-store routes, scoped queue and export, no public report links. Exercise two-tenant and revoked-user fixtures including pool reuse and worker claims | Engineering + Security |
| T2 · Invite/recovery takeover, guessing or operator misuse | High | Expiring hashed single-use tokens, session invalidation, hosted owner/operator MFA, generic messaging, throttles, and audited time-bound support access. Verify recovery, token races, session invalidation and break-glass policy | Identity + Platform |
| T3 · Unauthorized domain checks or load abuse | High | Owner attestation and independent TXT proof, exact-name scope, server-side flag, fixed resolver, limited job types and budgets, expiry/revocation checks, no arbitrary protocol or address. Verify policy enforcement with synthetic fixtures and an owned zone | Security |
| T4 · Untrusted data leaks or renders unsafely | High | Structured allowlisted inputs, safe escaping, size bounds, stable snapshot schema, no raw DNS, no personal/posture data in logs, no public source maps. Verify redaction, rendering and build exposure | Engineering + Privacy |
| T5 · Incorrect score, destructive race or duplicate actions | Medium | Version rule inputs, atomic writes, revision checks and idempotency. Reconcile approved snapshots with fixtures. Verify retry, concurrent edits and failing transactions | Engineering |
| T6 · Data loss or restored deletion | High | Encrypted, isolated backups. Verify periodic restore, deletion ledger replay and tenant-scoped extraction in a restricted environment | Platform + Privacy |
| T7 · Misleading findings or risky guidance | Medium | Show evidence source and limits, distinguish self-report and inconclusive observations, apply human content review and provide a feedback path | Product + Security |
| T8 · Compromised build, provider or deployment credential | High | Minimal service identities and egress, lock and scan dependencies, signed release provenance, protected deploys, rotatable credentials and alerts | Release + Platform |

## Authorized DNS behavior

Only the owner initiates verification and checks. Normalize and validate domain names server-side. Support exact public domains and reject address literals, reserved or internal suffixes, wildcards and unsupported names. Bind a random expiring TXT challenge and the authority attestation to workspace, exact name and proof generation. Challenge expires in 48 hours and verification expires 30 days after success. Renew with fresh proof. Never use resolver results as a connection destination. Query only the fixed verification TXT location and the two required public configuration locations. A successful challenge permits only the recorded scope. Revocation, closure and the kill switch reject new dispatch; work already sent to the resolver may finish and stale results must be discarded. Audit state changes with opaque IDs.

Provisional limits are five domains per workspace, one concurrent DNS job per workspace, two global in flight, 10 verification attempts and five check runs per workspace per day, and one check per exact name per hour across workspaces. Enforce caps atomically across retries and classify timeouts as inconclusive. Keep a hard overall deadline of 15 seconds per DNS job and allow at most one bounded transient retry inside the budget. Use controlled resolver configuration, timeouts and size limits. Apply a similar budget to invitation and recovery mail. Verify isolation and graceful degradation before enabling the checks flag for pilot workspaces.

## Privacy and handling

| Data / purpose | Parties with access | Lifecycle |
|---|---|---|
| Account email, credentials and membership for identity | User, scoped app, limited operator for account support, relay for delivery fields | Account lifetime, expiring access links, revoke sessions on removal/reset. Close or anonymize identity where no workspace requires it |
| Assessment, posture, actions, reports and workspace exports | Current workspace members subject to role, narrowly scoped verified support if authorized | Data lifecycle and immutable report rules in [schema](05-backend-schema.md). Record the reason for support access |
| Public domain name and coarse DNS outcomes for checks | Workspace, worker and approved resolver for fixed query names | Proof expiry, 90-day observations, separate report copies. Never persist raw resolver payloads |
| Security audit and operational metadata | Restricted operators and authorized privacy/security reviewers | 180-day audit and 30-day operational logs, no raw form bodies or secrets |
| Backup and deletion ledger for continuity | Dedicated recovery identity and restricted privacy records operator | 30-day backup expiry, replay deletion ledger before reopening; retain only opaque deletion metadata as needed to enforce this |

Before live records, confirm operator identity, purpose and lawful basis by category, processor contracts and transfer safeguards, retention and rights deadlines, and whether a formal impact assessment or registration applies. Owners receive protected export/closure via verified requests; individual rights use the operator channel. Report handling is explained before printing because a local PDF travels outside platform access controls. Escalate suspected disclosure through the approved incident route. See [website trust and jurisdiction](15-website-trust-compliance.md).
