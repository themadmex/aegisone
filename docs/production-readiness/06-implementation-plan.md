# Implementation plan

## Visible task plan

- [x] Inspect workspace and evaluate shared-chat context.
- [x] Define the six foundation artifacts.
- [x] Draft assurance, privacy, test and release records.
- [ ] Founder accepts scope and assigns implementation and release owners.
- [ ] Review architecture and clear each build slice.
- [ ] Collect staging, operational and pilot evidence.

Build sequencing assumes one engineer with part-time product/platform support. Estimate six to eight engineering weeks after approval, subject to identity, DNS authorization, and evidence spikes. Schedule pilot observation separately. Role owners below are assignments to confirm with the founder.

| Slice | Outcome and proposed surface | Dependency | Acceptance and evidence | Owner / status |
|---|---|---|---|---|
| S1 · Workspace and identity | Local Compose, CI, Django identity/workspace, MFA, invite/session, RLS | Gate 1 approval and review of auth/bootstrap design | FR-01 and restricted seed. Two-tenant requests, RLS, invite/recovery and MFA tests. Baseline build and changelog | Engineering / **in progress** (22 Nov 2026): 33 PostgreSQL tests pass locally. Invite → account → MFA → overview → invite contributor verified by hand in a browser. CI not yet run on GitHub. Open: encrypt TOTP secrets, shared rate-limit cache before scale-out, phone Menu button, self-hosted Geist fonts, independent review |
| S2 · Assessment and actions | Versioned catalog, assessment transactions, action service, mobile overview | S1 and reviewed assessment copy | FR-02–04 with score fixtures, replay/race tests, and a phone demonstration of first action | Engineering + Product / planned |
| S3 · Reports and rights | Snapshot/print, workspace data requests, scoped support runbook, retention | S2 | FR-06/07, snapshot/tenant checks, export isolation, deletion and policy review | Engineering + Privacy / planned |
| S4 · Domain checks | DNS proof and bounded worker checks, status view, feature kill switch | S1 and S2, design review and controlled test zone | FR-05 with synthetic resolver and authorized zone, revocation races, isolation/quotas, DNS outage drill | Engineering + Security / planned |
| S5 · Distribution and pilot readiness | OCI release, docs, third-party notices, dashboards, staging and recovery | S1–S4 | FR-08, NFR-01–07, clean self-host install, independent review, operations drill and sign-off | Release + Platform / planned |

**25 November candidate.** S2 assessment and actions, S3 reports and rights workflows, and the S4 opt-in DNS queue are implemented in the workspace. S5 has a verified local image, browser evidence, dependency audit and synthetic restore. The historical plan above records the original handoff. See the [current status, findings and remaining gates](16-slice-audit-and-verification.md).

Before each slice perform the [four-question review](11-four-question-review.md), confirm failure cases and collect evidence in staging. Environments are local/synthetic, private staging/synthetic, and hosted pilot with separate credentials and databases. Document repository structure, lockfiles, test commands and evidence links as implementation lands. Verify WCAG and apple-design interaction behavior with each affected UI slice. Seed a public demo only with synthetic data.

A slice is done when acceptance and key failure paths pass, migration and rollback implications are rehearsed as relevant, and code, docs, and deployment evidence are reviewed. See [test mapping](09-test-and-traceability.md), [rollout and rollback](10-operations-and-recovery.md), and [stage gates](12-release-readiness.md). Runtime and independent review evidence are pending.
