# Security Policy

## Supported Versions

AegisOne Open is currently in `0.1.x` pilot development. Security fixes are applied to the `main` branch.

| Version | Supported |
|---|---|
| `0.1.x` (`main`) | Yes |

## Reporting a Vulnerability

Please **do not** open public GitHub issues for suspected security vulnerabilities, authentication bypasses, tenant-isolation (`ROW LEVEL SECURITY`) flaws, or DNS verification bypasses.

Instead, report vulnerabilities privately through [GitHub Private Vulnerability Reporting](https://github.com/themadmex/aegisone/security/advisories/new) on this repository.

When reporting, please include:

1. Affected component, route, or management command.
2. Clear reproduction steps or a minimal proof-of-concept test against a local disposable Compose instance.
3. Expected security boundary vs. observed behavior (for example, cross-workspace data visibility under `aegis_app` or session revocation bypass).

We aim to acknowledge reports within **72 hours**, confirm severity and remediation timelines within **7 days**, and credit reporters upon coordinated disclosure if desired.

## Security Architecture Notes

- Tenant isolation is enforced in PostgreSQL via `FORCE ROW LEVEL SECURITY` using a dedicated runtime role (`aegis_app`) without `BYPASSRLS`.
- Authentication requires Argon2 password hashing and mandatory TOTP multi-factor enrollment with single-use recovery codes.
- Strict Content Security Policy (`default-src 'self'`, zero third-party scripts) is applied to all responses.
- Authorized domain checks require explicit owner attestation and cryptographic DNS TXT challenge verification before any public SPF/DMARC lookup runs.
