# Operations, rollout and recovery

The founder names a release authority, primary platform operator, alternate, privacy contact, and independent reviewer before pilot onboarding. Product owns guidance and customer communication. Security and Privacy share incident triage. Operators maintain working escalation contacts and a staffed coverage window. The closed pilot starts only after the on-call and escalation drill.

| SLI | Pilot objective / response |
|---|---|
| Core availability | 99.5% monthly synthetic sign-in plus assessment read/save using a dedicated synthetic tenant. Alert after three consecutive minute failures. Review the error budget weekly and freeze onboarding if exhausted |
| Speed | Meet NFR-03. Investigate p95 server latency above 500 ms for 15 minutes while traffic is representative |
| DNS job queue | Alert when oldest eligible job exceeds 2 minutes for 5 minutes or worker heartbeat is missing for 2 minutes. Shed checks first if core availability is affected |
| Integrity and privacy | Any suspected boundary escape or unauthorized DNS execution triggers immediate triage, feature containment and onboarding pause |
| Spend | USD 150/month provisional ceiling. Alert at 50%, 80%, and forecast breach. Review weekly usage and cost per active workspace. Keep fixed instance caps and explicit resolver/mail budgets |
| Recovery | 24h RPO and 4h RTO. Daily encrypted backups and 30-day expiry. Alert if backup is older than 24h or verification fails |

Log correlation ID, release, route category, normalized error category, duration and outcome with redaction and expiry. Audit actor and entity IDs are restricted. Never ingest raw form bodies, recovery links, DNS values or report contents. Check that monitoring itself meets data handling rules.

## Deployment and response

Release signed immutable images from protected CI after building, testing, scanning dependencies and secrets, generating SBOM and rehearsing migrations. Deploy compatible expand migrations first, then web and worker images, then smoke-test staging. Contract steps run only after the rollback window. Default DNS off in production and enable for accepted cohorts through server flags. Start with two invited SMEs for seven days, review activation, support tickets and guardrails, then expand to five to ten SMEs after product and operational review. Pause if the error budget is exhausted, severe accessibility blocks the core flow, or critical privacy/security controls fail. Preserve an assessment-only mode if the DNS service is unstable.

Rollback via previous signed compatible web/worker images, disable affected flags, stop relevant queue dispatch, and run private smoke tests for sign-in, save and report access. For incompatible data changes, isolate writes and follow the rehearsed forward fix or restore decision under release authority. Do not restore simply to roll back application code. Incident lead documents impact, containment, communication, potential notification duties and corrective actions.

## Restore drill

Quarterly and before launch, restore a representative encrypted backup to a private empty environment. Measure restore start to read/write smoke-test success against 4h RTO; compare the last restored committed marker with the estimated data-loss window against 24h RPO. Validate migrations, row counts, ownership and boundaries, then replay deletion and membership revocations from authoritative records and reject stale authorization. Pause reopening when reconciliation cannot establish current membership. Invalidate restored sessions and outstanding access tokens before reopening. Verify recovery data retains restrictions and securely retire drill resources. Exercise tenant-scoped extraction and reconciliation from the isolated restore without overwriting healthy tenants.

Use a bounded staging game day for mail outage, resolver timeout, worker restart/lease expiry, and backup failover. Abort on unexpected external traffic, workload or isolation failure. Keep customer data out of experiment logs. Single-region dependence is a pilot risk with named acceptance due at Gate 6.
