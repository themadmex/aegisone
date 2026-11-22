# Thirteen production layers

All layers apply. Use these design decisions and capture production-equivalent evidence in the referenced test or gate record.

| # | Layer | Design and gap to verify | Owner | Planned evidence | Status |
|---|---|---|---|---|---|
| 1 | Frontend foundations | Server-rendered responsive HTML, form fallback and no private client caching | UX | V05, V07, V09, V10 | NOT VERIFIED |
| 2 | APIs and backend logic | Scoped route contracts, state revisions, immutable submissions, bounded jobs | Engineering | V02–V05, V08 | NOT VERIFIED |
| 3 | Database and storage | RLS and composite keys, encrypted backups, expand-contract | Engineering | V06, V08, V11 | NOT VERIFIED |
| 4 | Authentication and permissions | Invite-only accounts, MFA, tenant roles and audited escalation | Security | V01, V08 | NOT VERIFIED |
| 5 | Hosting and deployment | Isolated local/stage/pilot, immutable rollout and rollback | Release | V07, V11 | NOT VERIFIED |
| 6 | Cloud and compute | Private DB, TLS proxy, restricted worker identities/egress, provider selection pending | Platform | V04, V07, V11 | NOT VERIFIED |
| 7 | CI/CD and version control | Protected review, pinned inputs, SBOM and signed provenance | Release | V07 | NOT VERIFIED |
| 8 | Security and row-level security | Current role checks, forced RLS, separate migration role and worker claims | Security | V01, V04, V08 | NOT VERIFIED |
| 9 | Rate limiting | Auth, domain and mail scope caps, noisy-neighbor isolation | Security | V01, V04, V10 | NOT VERIFIED |
| 10 | Caching and CDN | Versioned static caching and private no-store. Dedicated CDN decision deferred until measured need | Engineering | V05, V08, V10 | NOT VERIFIED |
| 11 | Load balancing and scaling | Single pilot region, proxy health checks and bounded workers. Horizontal load balancing conditional on demand | Platform | V10, V11 | NOT VERIFIED |
| 12 | Error tracking and logs | Redacted operational metrics, bounded retention and restricted audit | Platform | V06, V12 | NOT VERIFIED |
| 13 | Availability and recovery | 99.5% core SLO, 24h RPO, 4h RTO, restore and rollback rehearsal | Platform | V11, V12 | NOT VERIFIED |
