# Production security verification

Record release revision, environment, redacted evidence and retest results under [test traceability](09-test-and-traceability.md). Use reviewed controls and synthetic accounts for verification.

| Area | Applicability and enforcement | Owner | Verification | Status |
|---|---|---|---|---|
| Secrets and exposed files | Keep service credentials server-side, disable debug and public maps, protect CI and staging | Release | V07 scan Git/history, config, assets, maps and operational logs, then manually review hits | NOT VERIFIED |
| Authentication, MFA, recovery and sessions | Expiring tokens, revocation, MFA, generic errors and scoped cookies. No JWT API in this release | Security | V01 expiration, replay, enumeration, recovery and logout tests | NOT VERIFIED |
| Object, function and tenant authorization | Verify current role, scope all reads and mutations, restrict support and worker access | Security | V08 direct requests with synthetic identities, deny wrong tenants and unauthorized state changes | NOT VERIFIED |
| Database roles, storage and RLS | Force RLS, no broad app/worker privileges, separate recovery and migration roles | Engineering | V08 unset scope, connection reuse, composite links, and claimant grants. V11 backup isolation | NOT VERIFIED |
| Injection, XSS and CSRF | Parameterize database access, escape output, require CSRF, validate structured fields | Engineering | CI fixtures and staging configuration review in V05, V08 | NOT VERIFIED |
| Outbound requests and CORS | Resolver/relay-only worker egress, fixed task types, no cross-origin credential access | Security | V04 approved controlled-zone and simulated resolver tests, V08 same-origin review | NOT VERIFIED |
| Abuse and rate limits | Atomic counters, distinct auth and DNS budgets, overload and revocation behavior | Security | V01, V04, V10 cap, retry and concurrency checks | NOT VERIFIED |
| Debug, errors and sensitive logs | Redaction, restricted audit, reviewed staging access and minimal public health | Platform | V07, V12 confirm production settings, storage and alert redaction | NOT VERIFIED |
| Upload and path handling | NOT APPLICABLE to user uploads and user-controlled file paths. Reports are scoped HTML rows | Engineering | Reassess on adding file input | NOT APPLICABLE |
| Payments, webhooks and entitlements | NOT APPLICABLE. Free pilot with no payment integration, webhook surface or paid entitlement | Product | Reassess if billing or external callbacks enter scope | NOT APPLICABLE |

Confirmed privileged credential exposure requires immediate containment and rotation, impact assessment, and a retest. Any high-risk mandatory check without evidence blocks release.
