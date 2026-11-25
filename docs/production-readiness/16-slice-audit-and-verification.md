# Slice audit and verification

## Baseline and release verdict

**NO-GO for a general release.** The committed live pilot responds on `/healthz`. The working copy initially had 35 passing PostgreSQL tests and one failure. An uncommitted public landing route shadowed the protected workspace overview, so the password-reset session regression reached the landing page instead of exercising authorization. Engineering owns route separation and retesting. Existing landing assets are in scope for regression checks.

The PRD, TRD, UX specification, app flow, schema and implementation plan are available in this directory. The current work proceeds under the user's request to continue the defined slices. The hosted database and live release are outside this local implementation and verification run.

| Slice | Work and acceptance | Owner and status |
|---|---|---|
| S1 | Preserve the public landing and distinct protected overview. Retest identity, session revocation and PostgreSQL runtime roles. | Engineering, in progress |
| S2 | Implement the 20-question catalog, resumable assessment, immutable scored submissions, action history and dashboard. Verify scoring, replay, concurrency and tenant access. | Engineering and Product, in progress |
| S3 | Implement private report snapshots, revocation, print and owner data request intake. Review access, exports, retention and support operations. | Engineering and Privacy, pending |
| S4 | Implement an opt-in DNS proof and bounded worker for authorized domains. Verify stale proofs and resolver outcomes with isolated fixtures. | Engineering and Security, pending |
| S5 | Verify the release image, self-host workflow, accessibility, operational recovery and trust pages. Collect evidence and update verdict. | Platform and Release, pending |

## Design review before implementation

| Slice | Secure design | Efficient design | Regression risk | Required evidence |
|---|---|---|---|---|
| S1 | Distinct public and protected routes, retaining existing MFA and workspace authorization. | Route dispatch performs no extra network work. | Bookmarks, sign-in redirects and unauthenticated navigation. | Landing and protected overview behavior, session regression suite. |
| S2 | Forced PostgreSQL tenant policies, server-derived scores, versioned rules and transactional, revisioned mutations. | One draft per workspace, capped catalog and bounded dashboard queries. | Lost answers, duplicate submissions, action state overwritten by replay. | Golden scores, stale and duplicate requests, action recurrence, unrelated-workspace access and browser flow. |
| S3 | Server-built reports, private snapshots, permission-checked revocation and owner-only request intake. | Copy bounded data on save and use browser printing. | Stale previews, export overexposure, closed-workspace access. | Snapshot and report access tests, print, rights and restoration exercises. |
| S4 | Explicit proof and fixed SPF/DMARC lookups with lease, proof and authority checks. | On-demand bounded requests with durable status. | Expired proof, stale results and resolver degradation. | Synthetic resolver and owned-zone integration, quotas, revocation and worker tests. |
| S5 | Restricted release secrets and separate migration role. | Reuse OCI and CI entry points. | Image installs, migration rollback, recovery and unsupported claims. | Clean install, asset and dependency evidence, restore, release review. |

Risk tier 2 applies because workspaces hold private security posture. Tenancy, resilience, cloud cost, Django/PostgreSQL and browser interface overlays apply. The current release contains deterministic assessment rules and no AI feature. Independent review, legal approval, measured operational recovery and live pilot acceptance are unverified.

## Findings and disposition

| Severity | Finding | Disposition and evidence |
|---|---|---|
| High | The draft landing route shadowed the workspace route and invalidated the session-revocation check. | Resolved locally. The public URL is `/` and the protected route is `/overview`. The PostgreSQL suite and browser journey verify the distinction. |
| High | The first browser run rejected invite POSTs because the token page's referrer policy suppressed the request origin. Failure logging could include the token path. | Resolved locally. Invite and recovery responses use strict-origin and no-store. Django message filters redact account link paths, and the container access log records method, status and duration. The invite and MFA workflow passed in both browsers. Platform-level URL logging and retention still require verification. |
| High | The locked DNS dependency had two known advisories at 2.8.0. | Resolved. Updated to 2.9.2 and reran the strict dependency audit. No known advisories were reported by that run. |
| High | The current shared pilot deployment uses process-local auth rate limiting and stock Django OTP device secret storage. | Open. Security and Platform must implement and test a distributed limit and encrypted factor secret storage before general release. |
| High | DNS production execution requires a restricted worker identity, controlled egress and an owned DNS test zone. | Open. The feature defaults off. The local worker uses explicitly configured workspace IDs and fixture-tested proof, quota, expiry and revocation controls. Workload isolation, real-zone evidence and hosted scheduler setup remain unverified. |
| High | Representative recovery, reconciled tenant deletion, independent assurance and rights approvals are missing. | Open. The synthetic restore and retention dry run establish only local behavior. Privacy, Platform and Release must approve the policy and repeat the drills in isolation before launch. |
| Medium | The first landing-page accessibility scan found definition-list semantics and contrast issues. | Resolved for the tested viewports. Replaced the invalid list markup and improved contrast while preserving the landing design. Manual assistive technology and physical device checks remain open. |
| Medium | Image build context could include Vercel link state and local dotenv files. | Resolved locally. The build excludes both, runs as UID 10001, and the running image inspection found neither. |
| Medium | Source-distribution and landing-asset licensing, alert routing, capacity, budget thresholds and signed build provenance lack approval or evidence. | Open with Founder and Release. Existing GSAP and ScrollTrigger banners reference the GreenSock Standard License. Three.js bundles retain their license notice. Confirm the landing assets' provenance and distribution conditions and approve the project license before publication. |

## Verification and release gates

| Gate | Status | Observed evidence or requirement |
|---|---|---|
| 0 · Opportunity | PARTIAL | Product, users, pilot metrics and limits are in the planning pack. Pilot measurements are pending. |
| 1 · Definition | PASS for local implementation | The six foundation documents are reviewable and guided implementation. The 20-question catalog remains subject to product and security copy review before pilot expansion. |
| 2 · Architecture and risk | PARTIAL | Server-authoritative scoring, row policies and private snapshots were implemented. Deployment identity separation, encryption and privacy review remain open. |
| 3 · Build quality | PASS for local verification | Frozen dependencies, fresh migrations, migration-drift check, deployment settings check, local OCI build and 47 passing PostgreSQL tests. |
| 4 · Verification | PARTIAL | Core flows passed in PostgreSQL, desktop Edge and 320 px Chrome mobile emulation. DNS used synthetic replies. Physical devices, screen readers, forced-colors and production-size load remain unverified. |
| 5 · Operational readiness | PARTIAL | Restored two synthetic submissions into a separate database in 2.14 seconds. The runtime role saw zero unscoped rows and one row in the selected workspace. Reversed and reapplied the export policy migration on the restored database. Production-sized recovery, encrypted off-host backups, alert delivery and deletion reconciliation are pending. |
| 6 · Release | NO-GO | No hosted migration or DNS enablement was performed. Gate 2, 4 and 5 evidence and named acceptance owners are required before general release. |
| 7 · Operate and improve | NOT VERIFIED | No qualifying cohort, representative load or operational measurement window yet. |

## Assurance scorecard

| Domain | Status | Evidence and accountable role |
|---|---|---|
| Product, users and value | PARTIAL | Score, resume, actions and report flows passed. Product owns moderated testing and adoption measures. |
| Experience, accessibility and trust | PARTIAL | Desktop and 320 px emulation, keyboard menu dismissal and focus return, normal motion, reduced-motion and forced-colors preference checks, print PDF, and zero axe findings on four sampled surfaces in each browser. UX owns assistive-technology and physical-device verification. Privacy owns notice approval. |
| Architecture, application and data | PARTIAL | Six additive feature migrations, forced tenant policies, immutable snapshots and bounded DNS jobs. Engineering owns production migration rehearsal and worker separation. |
| Security, privacy, safety and compliance | PARTIAL | Role, stale authorization, report revocation, expiry and retention tests. Security and Privacy own independent review, MFA key storage and rights reconciliation. |
| Quality engineering and delivery | PARTIAL | Functional suite, browser smoke and locked Python package scan pass locally. Release owns protected CI, SBOM, signed images, and asset provenance. |
| Reliability, operations and recovery | PARTIAL | Clean local install, isolated synthetic restore, resolver timeout and mail failure evidence. Platform owns load, alerting, operational failover and representative recovery. |
| Governance, economics and improvement | NOT VERIFIED | Founder owns approvers, pilot checkpoints and release authority. Platform owns spend alerts and measured capacity. |

### Production layers

| Layer | Status | Evidence or gap |
|---|---|---|
| Frontend | PARTIAL | Form journeys, responsive screenshots and limited automated accessibility checks. |
| Application and API | PARTIAL | PostgreSQL and browser paths verified against the pilot slice requirements. |
| Database and storage | PARTIAL | Forced RLS, write constraints and synthetic restore. Production backup and key controls pending. |
| Identity and permissions | PARTIAL | MFA, password changes and revocation tests. Shared auth limits and OTP encryption pending. |
| Hosting and deployment | PARTIAL | Local OCI runtime and live read-only health check. Candidate deploy not verified. |
| Cloud and compute | PARTIAL | Non-root container and bounded work; production worker firewall and service identity unverified. |
| CI/CD | PARTIAL | Existing workflow and local checks; no hosted CI run, attested SBOM or release signature for this candidate. |
| Security and row-level authorization | PARTIAL | New tables force RLS, direct runtime-role checks pass, and cross-workspace paths are covered. Independent review open. |
| Rate limiting | PARTIAL | Domain queue caps and cross-workspace dispatch lock implemented. Distributed authentication limits remain open. |
| Caching and CDN | PARTIAL | Private no-store and collected static assets verified. Candidate CDN asset and header checks pending. |
| Load balancing and scaling | NOT VERIFIED | No representative concurrency, capacity, budget alarm or multi-instance exercise. |
| Errors and logs | PARTIAL | App token path redaction and local mail failure behavior. Provider logs, alert routing and retention remain open. |
| Availability and recovery | PARTIAL | Synthetic point-in-time snapshot and migration replay only. Hosted RPO/RTO and deletion recovery unverified. |

## Four-question review at verification and release

1. **Security.** PostgreSQL scopes tenant data and enforces immutable submissions and report content. Authorization is checked on each private request and DNS dispatch and completion. The app uses the existing runtime identity in the local worker, and release remains gated on a separate identity, worker egress and independent review.
2. **Efficiency.** Questions and guidance are source-controlled by catalog version. A bounded 20-answer JSON document avoids extra reads. Domain work runs on demand and report printing runs in the browser. Verify capacity and workload isolation before enabling richer data or increasing the cohort.
3. **Regression risk.** Existing root links now enter the public landing for anonymous visitors. Protected links use `/overview`. New feature tables require additive migrations before the candidate application starts. Old report snapshots remain independent of later inputs. Vercel routing and background worker scheduling have not been exercised for this candidate.
4. **Required tests.** Local PostgreSQL integration, desktop and mobile browser flow, print PDF, dependency audit, migration replay and scoped synthetic restore passed. Production-size recovery, deletion reconciliation, restore of revocations, assistive technology, real DNS proof, configured pilot email for the new request templates, and operating cost and alert drills remain release gates.

## Implementation choices and evidence inventory

- Assessment answers use a fixed, validated JSON document on an immutable submitted assessment. Action activity and report snapshots have separate tenant-owned relations. The proof challenge is derived from the secret key, workspace, name and proof generation. Rotating the key invalidates the displayed challenge until renewed.
- Support actions require explicit workspace and request identifiers. Export contains the workspace's submitted assessments, action state and recent DNS observations. It omits member email, authentication data and audit payloads. The retention command defaults to a preview. Closure takes effect immediately for access and stops queued work. Physical deletion of closed tenant data and restore reconciliation require an approved process.
- Test commands include `python -m pytest -q`, `manage.py makemigrations --check --dry-run`, `manage.py check --deploy --fail-level WARNING`, the strict `pip-audit` run over the frozen export, Compose build/start and `node tests/browser_smoke.cjs`. Browser evidence comprises desktop and mobile assessment and overview screenshots, the saved report print PDF and sanitized axe results. The local smoke test used synthetic accounts and never used live customer data.
- Release risk owners are roles awaiting founder assignment. This was a self-review. No signed compliance or production readiness claim is made.
