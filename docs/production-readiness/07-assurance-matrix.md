# Assurance domains and overlays

The hosted pilot is Tier 2. At Gates 1 and 2 the following proposed overlay decisions apply. Gate 2 review is pending. Active requirements are traced below and in the test plan.

| Overlay | Gate 1 / Gate 2 | Rationale and added release checks | Owner |
|---|---|---|---|
| AI, ML and autonomous behavior | NOT APPLICABLE / NOT APPLICABLE | Guided catalog and checks use deterministic rules. Each DNS job needs an owner request. No model, agent or autonomous security follow-up. Routine retention and delivery jobs are governed by the core automation domain | Product |
| Multi-tenant | ACTIVE / ACTIVE | Shared database and queue. Require RLS, scoped bootstrap/leases, private outputs, two-tenant tests and reviewed restore | Security |
| Resilience and chaos | ACTIVE / ACTIVE | Tier 2 with mail, DNS and DB dependency. Require staging failure drills, bounded retries and measured restore | Platform |
| FinOps | ACTIVE / ACTIVE | Hosted compute, resolver and mail can incur spend. Confirm budget, billing alerts and enforce usage bounds | Platform |
| Stack-specific blueprint | ACTIVE / ACTIVE | Django authorization/session defaults and PostgreSQL RLS affect security. Verify deployment checks, patch support and pooled scoping | Engineering |
| Browser design | ACTIVE / ACTIVE | Apply apple-design to rapid feedback, spatial consistency, interruptibility, typography and preference support. Explicit manual input-parity review | UX |

All 40 domains apply at pilot-appropriate depth. H is high risk; M is medium. Evidence refers to production-equivalent runtime or operational evidence. See [traceability](09-test-and-traceability.md) and [stage gates](12-release-readiness.md) for the verification plans and design review status.

| # | Domain | Risk | Proposed control or outcome | Verification | Owner | Evidence | Status |
|---|---|---|---|---|---|---|---|
| 01 | Problem and market validation | M | Owner/IT interviews and phone task validation | Gate 0 notes and pilot intent | Product | None yet | NOT VERIFIED |
| 02 | Product strategy and scope | M | Early posture-to-action focus and bounded pilot | Founder scope decision and activation review | Founder | None yet | NOT VERIFIED |
| 03 | Requirements and traceability | H | Acceptance criteria for all IDs and test coverage | V01–V12 mapping reviewed and populated | QA | None yet | NOT VERIFIED |
| 04 | Success metrics and analytics | M | Aggregate cohort funnels and approval guardrails | Reconcile metrics against synthetic records | Product | None yet | NOT VERIFIED |
| 05 | Experimentation and lifecycle | M | Cohort rollout, reversible DNS flag and retire plan | Flag rollback drill and pilot review | Release | None yet | NOT VERIFIED |
| 06 | UI foundations and design system | M | Shared responsive components and status states | V09 and responsive screen review | UX | None yet | NOT VERIFIED |
| 07 | UX flows and states | M | Recovery paths for offline, stale, denied and empty states | V02, V05, V09 | UX | None yet | NOT VERIFIED |
| 08 | Accessibility and inclusive design | H | WCAG AA target and equivalent input/preference modes | V09 automated and manual outputs | UX | None yet | NOT VERIFIED |
| 09 | Internationalization and localization | M | English, UTC persistence, local timezone and translatable strings | Timezone and expanded-string fixtures | Engineering | None yet | NOT VERIFIED |
| 10 | Trust, support and transparency | H | Evidence limitations, consent at the point of authorization, published support | V04, V12 policy and UX evidence | Product | None yet | NOT VERIFIED |
| 11 | Frontend foundations | H | Progressive enhancement, no exposed secrets, accessibility and performance | V07, V09, V10 | Engineering | None yet | NOT VERIFIED |
| 12 | API and backend logic | H | Validated mutations, revisions, versioned rules and idempotency | V02–V05, V08 | Engineering | None yet | NOT VERIFIED |
| 13 | Database and storage | H | Composite keys, scoped rows, encryption, migrations and backups | V06, V08, V11 | Engineering | None yet | NOT VERIFIED |
| 14 | Architecture and maintainability | M | Small modular monolith and explicit service boundaries | Gate 2 review and module ownership | Engineering | None yet | NOT VERIFIED |
| 15 | Data governance and quality | H | Catalog and snapshot provenance, purpose, retention and deletion | V02, V05, V06 | Privacy | None yet | NOT VERIFIED |
| 16 | Dependencies and resilience | H | Contain resolver/relay failures, cap retries and reopen core flows | V04, V11 dependency drills | Platform | None yet | NOT VERIFIED |
| 17 | Authentication and authorization | H | MFA, recovery/session checks, roles and row isolation | V01, V08 | Security | None yet | NOT VERIFIED |
| 18 | Application and infrastructure security | H | Controlled egress, verified proof, safe defaults and scoped credentials | V04, V07, V08 and review | Security | None yet | NOT VERIFIED |
| 19 | Abuse prevention and rate limiting | H | Atomic budgets for auth, invite and DNS, feature switch | V01, V04, V10 | Security | None yet | NOT VERIFIED |
| 20 | Supply-chain security | H | Pinned inputs, advisory checks, SBOM and signed output | V07 attestation and scan results | Release | None yet | NOT VERIFIED |
| 21 | Privacy engineering | H | Purpose-based collection, export/closure, no tracking, redaction | V06, V12 and processor review | Privacy | None yet | NOT VERIFIED |
| 22 | Safety and responsible automation | H | Manual check initiation, bounded worker and honest guidance | V03, V04 and content review | Security | None yet | NOT VERIFIED |
| 23 | Legal, regulatory and policy compliance | H | Resolve operator and local obligations before release | Compliance record and qualified review | Founder + Privacy | None yet | NOT VERIFIED |
| 24 | Test architecture | H | Unit, PostgreSQL integration, browser and controlled resolver fixtures | V01–V12 repeatable checks | QA | None yet | NOT VERIFIED |
| 25 | Non-functional verification | H | Performance, accessibility, isolation and resilience budgets | V08–V11 | QA | None yet | NOT VERIFIED |
| 26 | Version control and CI/CD | H | Protected review, pinned CI and promoted verified images | V07 pipeline dry run | Release | None yet | NOT VERIFIED |
| 27 | Release engineering | H | Compatible migrations and phased rollout with flag and image rollback | V07, V11, V12 | Release | None yet | NOT VERIFIED |
| 28 | Environment and configuration | H | Separate environments, secrets and validated deployment settings | V07, V12 and config review | Platform | None yet | NOT VERIFIED |
| 29 | Hosting, cloud and networking | H | Private DB, TLS, resolver/relay-only worker destinations and owned config | V04, V07, V11 | Platform | None yet | NOT VERIFIED |
| 30 | Caching and performance | H | Cache versioned public assets, avoid caching private data, set page/query budgets | V05, V08, V10 | Engineering | None yet | NOT VERIFIED |
| 31 | Load balancing and scaling | M | Bound queue and concurrency, health checks and overload behavior | V10, V11 capacity and saturation drill | Platform | None yet | NOT VERIFIED |
| 32 | Observability and error tracking | H | Correlatable redacted logs, metrics, audit and alerts | V12 alert and redaction evidence | Platform | None yet | NOT VERIFIED |
| 33 | Service reliability | H | SLOs and error budget govern rollout, dependencies degrade separately | V10–V12 and staged metrics | Platform | None yet | NOT VERIFIED |
| 34 | Incident response and ownership | H | Named incident lead/alternate, contact tree and playbooks | V11, V12 operational drill and roster | Platform | None yet | NOT VERIFIED |
| 35 | Availability, backup and recovery | H | Encrypted recovery copies, measured restore and deletion replay | V11 timing, isolation and recovery evidence | Platform | None yet | NOT VERIFIED |
| 36 | Governance and decisions | H | Record sign-off, scope, risks, due dates and owners | Gate records and residual-risk approvals | Founder | None yet | NOT VERIFIED |
| 37 | Cost and sustainability | M | Pilot ceiling, alerts and unit cost, capacity caps | V10, V12 and provider quote | Platform | None yet | NOT VERIFIED |
| 38 | Knowledge continuity | M | Install/update, architecture, support and operator guides | Independent walkthrough plus V07 | Engineering | None yet | NOT VERIFIED |
| 39 | Delivery performance and team health | M | Track lead time, rework and incident toil, confirm support coverage | Gate 7 monthly review and roster | Release | None yet | NOT VERIFIED |
| 40 | Continuous improvement and retirement | M | Review funnel outcomes, budget, incidents; rehearse retiring a flag or tenant | Gate 7 action log and V06 evidence | Product | None yet | NOT VERIFIED |
