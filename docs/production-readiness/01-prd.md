# Product requirements

The release helps an SME turn a short assessment into an explainable action plan, follow progress, and share a point-in-time summary. The primary users are a workspace owner who coordinates changes and an IT contributor who assesses and implements them.

| Role | Responsibilities |
|---|---|
| Owner | Manage membership and domains, complete assessments, update actions, generate reports, request workspace export or closure |
| Contributor | Complete assessments, update actions, view domain observations, create and view reports |
| Operator | Provision pilot invites and triage service issues. Customer-content access requires time-limited, audited escalation |

| ID | Feature | Acceptance criteria |
|---|---|---|
| FR-01 | Account and workspace | Invited users redeem a single-use link tied to their email and enter an authorized workspace. Owner can invite or remove contributors. Revocation applies on the next protected request. Maintain at least one owner. |
| FR-02 | Guided assessment | Answer 20 questions across accounts, devices and updates, backups, email and phishing, and incident readiness. Choices are Yes, Partly, No and Unsure. Save and resume across devices. Require all answers to submit. Submission is immutable and template-versioned. |
| FR-03 | Dashboard | Show the latest submitted score and date, separate draft progress, top three open actions, and recent domain observations. Yes earns 2, Partly 1, No and Unsure 0. Round the percentage half-up and show the Unsure count. Label the score as a self-reported baseline. Before submission show an assessment entry point and no score. |
| FR-04 | Prioritized actions and guidance | Versioned rules map each gap or observation to curated guidance with a reason, practical steps and a way to confirm the fix. Sort High, Medium, Low, then stable action key. Support Open, In progress, Done and Reopen with audit events. A newly observed recurrence reopens a Done action and preserves history. |
| FR-05 | Authorized domain checks | Owner attests authorization and proves control by publishing a DNS TXT challenge at the exact domain scope. Owner can request a bounded public DNS check for SPF and DMARC. Each result shows scope, observation time, outcome, limits and next step. Missing, present, needs review and inconclusive are distinct. The core assessment and report work without this feature. |
| FR-06 | Reports | Owner or contributor can preview and create an authenticated, dated, immutable HTML report with Print / Save as PDF. Include score, answers summary, prioritized actions and domain evidence with source and limits. The creator or owner can revoke it, and removed members lose access. |
| FR-07 | Help and data rights | Provide help, privacy and terms from signup and footer. Owner can request structured export or closure, see status, and receive confirmation after authority checks. Provide a route for individual rights requests. |
| FR-08 | Open distribution | Publish source, approved license, reproducible container build, install/update guides, sample data, vulnerability reporting and contribution guidance. Verify a clean install with no hosted account. |

SPF checks presence and obvious duplication of SPF-tagged records at the authorized name. DMARC checks record presence and recognizes the exact-name policy value. A missing exact-name record leaves inheritance undetermined. DNS failures are inconclusive. Results do not establish email delivery, a vulnerability, or policy enforcement. Advise provider review before restrictive email-policy changes. [SPF specification](https://www.rfc-editor.org/info/rfc7208/) · [DMARC specification](https://www.rfc-editor.org/info/rfc9989/)

Release 0.1 includes only these manually requested public DNS observations. Vulnerability monitoring, compliance support and privacy-conscious AI guidance are staged separately. No device agents, automated remediation, billing, attachments, or public report links are included.

## Pilot outcomes

- At least 70% of workspaces starting a draft submit within seven days. Moderated sessions target median completion within 15 minutes.
- At least 50% of workspaces with eligible High or Medium actions mark one Done within 30 days. Measure only cohorts with 30 days elapsed. This measures self-reported progress.
- Four of five moderated users can explain their highest-priority action and locate their report unaided.
- Zero confirmed cross-workspace disclosures or unauthorized domain checks. Either occurrence pauses onboarding.
- Record weekly aggregate funnel counts and show sample sizes. Pilot results are directional.

## Assessment catalog v1

Phrase each row as a question. Use Yes for consistently in place, Partly for incomplete coverage, No for absent and Unsure when the respondent cannot verify. Each question has equal weight and one action key. Review wording with pilot users and a security reviewer before enabling the catalog.

| ID | Section / practice to verify | Priority | Guidance outcome |
|---|---|---|---|
| Q01 | Accounts / MFA on administrative accounts | High | Enable MFA for all administrators and verify enrollment |
| Q02 | Accounts / MFA on company email accounts | High | Require MFA for staff email and check the completion list |
| Q03 | Accounts / individual staff logins | Medium | Replace shared day-to-day logins with attributable accounts |
| Q04 | Accounts / prompt removal of leavers' access | High | Add a leaver checklist and verify on a sample departure |
| Q05 | Devices / list of work computers and phones | Medium | Start a device register with an owner and update date |
| Q06 | Devices / supported operating systems | High | Identify unsupported devices and schedule replacement or upgrades |
| Q07 | Devices / timely security updates | High | Set a patch review routine and verify installation on a sample |
| Q08 | Devices / screen lock on work devices | Medium | Apply screen lock and verify on representative devices |
| Q09 | Recovery / regular backups of important business data | High | Identify essential data and verify successful backup runs |
| Q10 | Recovery / backup access restricted from daily accounts | High | Separate backup access and verify the access list |
| Q11 | Recovery / recent restore test | High | Restore a small representative sample and record elapsed time |
| Q12 | Recovery / documented recovery responsibilities | Medium | Name recovery owners and identify business priorities |
| Q13 | Email / process to report suspicious messages | Medium | Publish a reporting contact and run a practice report |
| Q14 | Email / independent confirmation of payment-detail changes | High | Establish a callback workflow using a known contact and rehearse it |
| Q15 | Email / staff guidance on unexpected links and attachments | Medium | Run a short briefing and use a recognition exercise |
| Q16 | Email / reviewed domain email-authentication settings | Medium | Ask the provider to review SPF and DMARC on sending domains |
| Q17 | Readiness / named incident lead | Medium | Assign a lead and alternate and confirm who is reachable |
| Q18 | Readiness / staff know escalation contact | Medium | Share the escalation path and verify staff can locate it |
| Q19 | Readiness / critical supplier support contacts recorded | Low | Record supplier contact and account ownership for emergencies |
| Q20 | Readiness / incident process rehearsed | Low | Run a short tabletop and record corrective actions |

Each Partly, No or Unsure yields the configured action. Unsure uses verification-first copy and retains the same priority. Stable keys use question ID for workspace findings and check type plus domain ID for DNS findings. DNS Missing or Needs review creates a Medium action only after the owner identifies the domain as used for sending mail. Inconclusive shows a recheck path and does not change priority or generate a finding. Preserve distinct observed and self-reported evidence. A later applicable gap recorded after a Done transition reopens the action. The same source event replay does not. A newer passing assessment or DNS observation removes the item from current suggestions while preserving history and prior human state. Report both current evidence and action status.

Golden fixtures include all Yes = 100, three Yes plus one Partly plus sixteen Unsure = 18, and all Unsure = 0 with twenty unconfirmed answers. The score uses the fixed applicable catalog. A future template with a different maximum requires a new rules version. Show the date and catalog version on every report.
