# Security Policy: Secrets, Credentials & Confidential Data

### 1. Core policy
INFERX must never store or publish secrets or confidential information in its Git repository. This applies to all branches, tags, commits, pull requests, releases, documentation, examples, tests, notebooks, build artifacts, and CI logs. A private repository is not a secrets vault.

### 2. Prohibited repository content
Never commit:
- API keys, bearer tokens, OAuth secrets, passwords, database credentials, connection strings containing credentials, cloud access keys, service-account JSON, signing keys, private keys, or private certificate material.
- Production or staging credentials, session cookies, recovery codes, webhook secrets, encryption keys, or secret-manager exports.
- Customer/user personal data, confidential business data, real production prompts or responses, database dumps, logs containing identifiers or tokens, or unredacted support/incident records.

Do not include real credentials in screenshots, Markdown, code comments, sample `.env` files, test fixtures, curl commands, terminal output, or commit messages.

### 3. Approved secret storage and configuration
- Developers keep local credentials in ignored files such as `.env` / `.env.local` or in an approved local secret store.
- Commit `.env.example` (and equivalent templates) containing only descriptive variable names and clearly fake placeholders. Never copy a real `.env` into a template.
- Production and staging secrets must be injected at runtime from the deployment platform's secret manager or protected environment configuration.
- Frontend code and browser-delivered bundles must never contain server-side secrets. Public client configuration must be explicitly classified as public.
- Use least privilege, separate credentials per environment and service, avoid sharing personal credentials, and rotate credentials on a defined schedule and immediately after suspected exposure.
- Keep signing keys, encryption keys, and certificates with private material outside source control and restrict access.

### 4. Git hygiene and ignore policy
Maintain and review `.gitignore` rules for:
- `.env` and `.env.*`, while explicitly allowing safe templates such as `!.env.example`.
- Private keys, credential files, service-account files, certificates with private material, and local secret-store exports.
- Local databases, database dumps, logs, temporary files, model caches, and generated artifacts that may contain sensitive data.

Ignore rules do not protect files that are already tracked. Verify repository tracking and staged changes. Never rely on deleting a sensitive file in a later commit to make an earlier exposure safe.

### 5. Commit and pull-request security gate
Before every commit, contributors must:
1. Review `git status` and inspect the full staged diff with `git diff --cached`.
2. Review staged filenames and file contents for secrets, confidential information, personal data, and accidental generated files.
3. Run a secret scanner (Gitleaks or an equivalent approved tool) against the staged changes.
4. Confirm no local environment files, credentials, private keys, database dumps, sensitive logs, or real user data are staged.
5. Run applicable tests and resolve all security-check failures before committing.

Do not blindly stage all files. Do not bypass hooks, scanners, CI checks, or branch protections. Pull requests must pass automated secret scanning and require maintainer review before protected-branch merges.

### 6. Exposure response
If a secret is committed, pushed, included in a PR, or otherwise exposed:
1. Assume it is compromised, regardless of whether the commit is public or private.
2. Immediately revoke or rotate the credential with its issuer. Rotation is mandatory; deleting the file or rewriting Git history does not invalidate the old credential.
3. Privately notify the repository maintainer/security owner. Never repeat the secret in an issue, chat, commit, log, or incident report.
4. Coordinate removal from repository history where appropriate, and assess forks, clones, CI logs, build artifacts, caches, releases, and deployments.
5. Document the incident using redacted details, verify the replacement credential is stored safely, and restore/verify all security controls.

### 7. Ownership and enforcement
The maintainer owns repository security policy, protected-branch settings, scanner configuration, and exception approval. Exceptions must be explicit, narrowly scoped, documented, and must never permit real credentials or confidential data to be committed. AI coding agents and contributors must follow the same controls and must not weaken them without maintainer approval.

### 8. Recommended implementation checklist
- Add and maintain `.gitignore` rules and a safe `.env.example`.
- Add Gitleaks (or an equivalent secret scanner) as a local pre-commit check and CI pull-request check.
- Protect `main` and release branches; require CI checks and maintainer approval.
- Keep deployment secrets in the hosting provider's secret manager.
- Add a security section to the contributor guide explaining how to report accidental exposure privately.

### 9. HTTP API trust boundary (v0.3.0)

- The API has **no authentication or authorization** yet. Bind to loopback (the default) or a trusted network; do not expose it publicly.
- Requests cannot select a model, load or unload models, or run code; unknown JSON fields are rejected.
- Prompts and generated text are never written to logs or error bodies; request IDs from clients are validated before use.
- Inputs are bounded (prompt length, output tokens, body size) and concurrency/waiting is bounded per process. Rate limiting per user arrives with identity (v3.3 / v4.0).
