# Release readiness and decisions

**Definition pack ready for review. Production verdict: NO-GO.** No runtime, customer validation, independent review, or restore evidence exists yet. The pack was self-reviewed.

| Gate | Status | Exit evidence |
|---|---|---|
| 0 · Opportunity | PARTIAL | Product hypothesis and pilot kill criteria documented. Interviews and usability research pending |
| 1 · Definition | PARTIAL | Six linked artifacts are ready. Founder confirms intended scope, owners and sequencing before build |
| 2 · Architecture and risk | PARTIAL | Draft designs and four-question analysis exist. Review identity, RLS/job boundaries, processor selection, privacy impact and cost plan |
| 3 · Build quality | NOT VERIFIED | Review each implementation slice, passing CI, migration practices and supply-chain coverage |
| 4 · Verification | NOT VERIFIED | V01–V12, applicable domain/layer reports and independent security review |
| 5 · Operational readiness | NOT VERIFIED | Named owner and alternate plus verified deploy/rollback, restore, alerts and runbooks |
| 6 · Release | NOT VERIFIED | Approval from named authority, residual-risk acceptance and reviewed pilot thresholds |
| 7 · Operate and improve | NOT VERIFIED | Weekly SLO, product, costs and incident review, with documented actions and ownership |

## Production-readiness scorecard

Score applicable domains 0–4 only with implementation evidence. The seven pillars currently have no production score. Mandatory and high-risk gaps block release regardless of score.

| Pillar | Production status | Primary gap / role owner |
|---|---|---|
| Product, users and value | NOT VERIFIED | Real pilot outcomes and user research / Product |
| Experience, accessibility and trust | NOT VERIFIED | Usability, accessibility and preference tests / UX |
| Architecture, application and data | NOT VERIFIED | Transaction and boundary verification / Engineering |
| Security, privacy, safety and compliance | NOT VERIFIED | Independent review, authorization and processor/rights evidence / Security + Privacy |
| Quality and delivery | NOT VERIFIED | Production-equivalent CI and release evidence / QA + Release |
| Reliability, operations and recovery | NOT VERIFIED | Alerting, SLO evidence and restore drill / Platform |
| Governance, economics and improvement | NOT VERIFIED | Named authority, budget, owner coverage and operating cadence / Founder |

No runtime risk has been accepted. High risks include unauthorized access/traffic, lost or resurrected data, and publication with unresolved third-party license obligations. Block release for any of those, critical user flow failures, unmet mandatory accessibility/security requirements, incomplete operational recovery, or unresolved legal blockers.

## Founder review

Confirm Nigerian invite-only pilot and the self-host target, the 20-question assessment and DNS-only scope, the proposed stack, the free core and proposed code license, operator identity and accountable people, and budget. Resolve jurisdiction and provider decisions before the appropriate deployment or publication gate. Approval by the founder is the handoff into implementation under the world-class software development skill.

### Open decision register

| Decision | Accountable role to confirm | Needed by | Evidence or disposition |
|---|---|---|---|
| Pilot cohort and support coverage | Founder | Gate 1 approval | Confirm age/sector boundaries, geography and recruitment plan |
| Identity and tenant/job boundary | Engineering + Security | Gate 2 | Threat review, package selection and explicit bootstrap/worker trust contracts |
| Hosting region and processors | Platform + Privacy | Gate 2 provider selection / before live data | Data-flow inventory, quote, contracts and reviewed transfer decisions |
| License and brand | Founder | Before publication | Confirm code license, third-party dependency notices and brand clearance |
| Single-region recovery residual risk | Release authority | Gate 6 | Review restore drill results, accept bounded exposure with a deadline and named owner or defer the pilot |
| Production readiness authority and independence | Founder | Before S5 | Name release owner, operator/alternate and independent reviewer; record review scope |
