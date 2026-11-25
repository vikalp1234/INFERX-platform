# Security Policy

## Supported versions

INFERX is pre-release. No version is supported yet; this table will be filled in at v0.1.0.

## Reporting a vulnerability or an exposed secret

Please report privately. **Do not open a public issue, and never paste a secret, token or private data into a report.**

- Use GitHub **Private vulnerability reporting**: the repository's *Security* tab → *Report a vulnerability*.
- Describe the affected component, steps to reproduce and impact. Redact any credentials.

If you accidentally committed a secret, assume it is compromised: revoke or rotate it with its issuer first, then notify the maintainer privately. Deleting the commit does not make the secret safe.

## Policy

The full secrets and confidential-data policy is in [docs/security-policy.md](docs/security-policy.md). Engineering rules for contributors and AI agents are in [CLAUDE.md](CLAUDE.md).
