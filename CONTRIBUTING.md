# Contributing to INFERX

Thanks for helping. Read [CLAUDE.md](CLAUDE.md) and the [master guide](docs/MASTER_IMPLEMENTATION_GUIDE.md) first.

## Flow

1. Open or pick an issue; agree scope and acceptance criteria.
2. Fork and create a feature branch.
3. Implement with tests and docs.
4. Open a pull request; CI must pass.
5. The maintainer reviews correctness, architecture, security and licensing, and controls merges and releases.

## Commits

Use Conventional Commit prefixes: `feat`, `fix`, `docs`, `test`, `chore`, `ci`. Keep commits small and focused.

## Development setup

Backend (Python 3.12, [uv](https://docs.astral.sh/uv/)):

```bash
cd backend
uv sync
uv run pytest
```

Install the hooks once: `pre-commit install`.

## Before every commit

1. `git status` and `git diff --cached`: review exactly what is staged.
2. Run `gitleaks protect --staged --redact`.
3. Run the relevant tests and linters.
4. Never stage `.env` files, keys, model weights, databases, logs or real user data. Stage files by name, not `git add .`.
5. Never bypass hooks or CI.

## Security: accidental exposure

If you commit a secret, revoke or rotate it first, then report it privately as described in [SECURITY.md](SECURITY.md). Never paste the secret into an issue, chat or commit.
