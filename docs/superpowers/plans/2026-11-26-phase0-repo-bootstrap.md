# INFERX Phase 0 — Repository Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the empty INFERX repo into a secure, CI-gated, documented skeleton (no inference code) ready for v0.1.0.

**Architecture:** Docs and governance at the repo root; a minimal `backend/` uv project (Python 3.12) that only proves tooling (ruff, pytest) works; secret scanning enforced locally (pre-commit + Gitleaks) and in CI; `main` protected so every later change goes through a PR.

**Tech Stack:** Python 3.12, uv, ruff, pytest, pre-commit, Gitleaks, GitHub Actions.

**Spec:** `MASTER_IMPLEMENTATION_GUIDE.md` (§5 repo structure, §13 security, §17 governance, §18 Phase 0 prerequisites) and `CLAUDE.md` (secrets rules, §17 Git) — source copies in `~/Downloads/INFERX_Security_Updated_Docs/`.

## Global Constraints

- Python **3.12**, package manager **uv** (lockfile `uv.lock` committed).
- Layout follows `CLAUDE.md` §10.3 (Clean Architecture); do **not** create empty layer packages in Phase 0.
- Never commit `.env*` (except `.env.example`), keys, model weights, local DBs, logs, dumps.
- Before **every** commit: `git status`, `git diff --cached`, `gitleaks protect --staged --redact`. Stage files by name; never `git add .` / `-A`.
- Never bypass hooks (`--no-verify`) or CI; never force-push `main`.
- Commit trailer: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Pushing is outward-facing on a public repo: confirm with the maintainer before each `git push`.
- No fabricated status: roadmap items stay PLANNED.

## Review Focus

- Pre-existing tracked files (`LICENSE`, `README.md`) must not be clobbered by the local files (Task 0 uses pull, not overwrite).
- `.gitignore` `.env*` rule must still allow `.env.example` (tested with `git check-ignore`).
- A staged fake secret must be **blocked** by the hook and by CI (tested in scratch, never committed).
- CI job names must exactly match the required-status-check names in branch protection.
- Docs split must not drop any rule from the original security block.

---

## Work breakdown (branch → PR per task, squash-merge)

| Task | Branch | PR title |
|---|---|---|
| 0 | (none) | local setup only |
| 1 | `phase0/gitignore-env` | chore: add .gitignore and .env.example |
| 2 | `phase0/docs-governance` | docs: add CLAUDE.md, master guide, security docs |
| 3 | `phase0/community-files` | docs: add README, CONTRIBUTING, CoC, CHANGELOG, templates |
| 4 | `phase0/backend-skeleton` | chore: add uv backend skeleton with ruff and pytest |
| 5 | `phase0/precommit-gitleaks` | ci: add pre-commit with gitleaks |
| 6 | `phase0/ci-workflow` | ci: add GitHub Actions (lint, test, secret scan) |
| 7 | (settings) | branch protection |

Tasks 1–3 are first merged by the maintainer before protection exists; Task 7 turns protection on last, after CI job names are proven.

---

### Task 0: Local tooling and repo connection

**Files:** none committed.

**Produces:** a local clone tracking `origin/main`, with `git`, `uv`, `gitleaks`, `pre-commit`, `gh` available.

- [ ] **Step 1: Install tools**

```bash
brew install uv gitleaks pre-commit gh
```

- [ ] **Step 2: Verify versions**

Run: `uv --version && gitleaks version && pre-commit --version && gh --version`
Expected: each prints a version; no "command not found".

- [ ] **Step 3: Authenticate GitHub CLI interactively**

Run: `gh auth login` (browser flow). Never paste tokens into files or chat.
Expected: `gh auth status` shows logged in as `vikalp1234`.

- [ ] **Step 4: Connect the non-empty folder to the remote (do not `git clone .`, folder contains `docs/`)**

```bash
cd "/Users/manvik/Desktop/workstation/AI Portfolio/INFERX-platform"
git init -b main
git remote add origin https://github.com/vikalp1234/INFERX-platform.git
git pull origin main
```

Expected: `ls` shows `LICENSE`, `README.md`, `docs/`; `git status` shows only `docs/` untracked.

- [ ] **Step 5: Set local identity (repo-scoped, use the GitHub noreply address, not a personal email)**

Run: `git config user.name "<name>" && git config user.email "<id>+vikalp1234@users.noreply.github.com"` — maintainer supplies values.

---

### Task 1: `.gitignore` and `.env.example`

**Files:**
- Create: `.gitignore`, `.env.example`

**Produces:** ignore rules every later task relies on.

- [ ] **Step 1: Branch**: `git switch -c phase0/gitignore-env`

- [ ] **Step 2: Create `.gitignore`** covering exactly these groups (policy §4):
  - Secrets: `.env`, `.env.*`, `!.env.example`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.crt` (private-material certs), `*credentials*.json`, `service-account*.json`, `secrets/`
  - Data: `*.db`, `*.sqlite`, `*.sqlite3`, `*.dump`, `*.sql.gz`, `*.log`, `logs/`, `tmp/`
  - Models/caches: `*.safetensors`, `*.bin`, `*.gguf`, `*.pt`, `*.pth`, `*.onnx`, `/models/` and `/backend/models/` (root-anchored so `app/domain/models/` stays trackable), `.cache/`, `huggingface/`
  - Python: `__pycache__/`, `*.pyc`, `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `dist/`, `build/`, `*.egg-info/`
  - Node/frontend: `node_modules/`, `frontend/dist/`
  - OS/IDE: `.DS_Store`, `.idea/`, `.vscode/` (except none allowed), notebooks checkpoints `.ipynb_checkpoints/`
  - Do **not** ignore `uv.lock` or `.python-version`.

- [ ] **Step 3: Create `.env.example`** with only descriptive names and unmistakable placeholders, each commented as local-only: `INFERX_ENV=development`, `INFERX_LOG_LEVEL=INFO`, `INFERX_MODEL_ID=HuggingFaceTB/SmolLM2-360M-Instruct`, `INFERX_MODEL_REVISION=REPLACE_WITH_PINNED_REVISION`, `HF_TOKEN=REPLACE_WITH_YOUR_TOKEN_IF_NEEDED` (placeholder text must not resemble a real token format).

- [ ] **Step 4: Verify ignore rules**

Run: `touch .env .env.local secrets_test.pem && git check-ignore -v .env .env.local secrets_test.pem; git check-ignore .env.example; echo "exit=$?"; rm .env .env.local secrets_test.pem`
Expected: the first three are reported as ignored; `.env.example` prints nothing and `exit=1` (not ignored).

- [ ] **Step 5: Commit**

```bash
git status
git add .gitignore .env.example
git diff --cached
gitleaks protect --staged --redact
git commit -m "chore: add .gitignore and .env.example" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

Expected: gitleaks reports "no leaks found".

---

### Task 2: Governance docs (CLAUDE.md, master guide, security policy)

**Files:**
- Create: `CLAUDE.md`, `docs/MASTER_IMPLEMENTATION_GUIDE.md`, `SECURITY.md`, `docs/security-policy.md`
- Source: `~/Downloads/INFERX_Security_Updated_Docs/{CLAUDE.md,MASTER_IMPLEMENTATION_GUIDE.md}`

**Decisions fixed here:**
- The "Security Policy" block prepended to the master guide (lines 1–56 of the source) becomes `docs/security-policy.md` verbatim (title `# Security Policy: Secrets, Credentials & Confidential Data`); the master guide then starts at `# INFERX — Master Product & Engineering Implementation Guide`.
- The "Mandatory Security & Secrets Management Rules" block at the top of `CLAUDE.md` (source lines 1–37) **stays** in `CLAUDE.md` (agents read it first); it gets a one-line pointer to `docs/security-policy.md`.
- `CLAUDE.md` duplicate numbering: the second `## 10. Architecture and code boundaries` becomes `## 11.`, and following headings shift +1 (11→12 … 19→20). Grep for in-text section references afterward and fix any broken ones.
- `SECURITY.md` is the short public reporting policy: report privately via GitHub **Private Vulnerability Reporting** (enabled in Task 7), never in public issues, never paste secrets; supported versions "pre-release, none yet"; link to `docs/security-policy.md`. No personal email.

- [ ] **Step 1: Branch**: `git switch -c phase0/docs-governance`

- [ ] **Step 2: Copy and split files per the decisions above** (`mkdir -p docs` already exists).

- [ ] **Step 3: Verify no rule was lost**

Run: `diff <(sed -n '1,56p' ~/Downloads/INFERX_Security_Updated_Docs/MASTER_IMPLEMENTATION_GUIDE.md) <(sed -n '1,56p' docs/security-policy.md)`
Expected: no diff (or only the intended blank-line trimming). Also `grep -c '^## ' CLAUDE.md` shows no duplicate numbers: `grep -E '^## [0-9]+\.' CLAUDE.md | awk '{print $2}' | sort | uniq -d` prints nothing.

- [ ] **Step 4: Commit** (staged by name; gitleaks as in Task 1) — `docs: add CLAUDE.md, master guide, and security policy`

---

### Task 3: Community and process files

**Files:**
- Create: `README.md` (overwrite 17-byte stub), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md`, `.github/CODEOWNERS`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/{bug_report.md,feature_request.md}`

**Content decisions:**
- `README.md`: name, tagline "Understand. Measure. Optimize.", one-paragraph vision, **status table copied from guide §21 (all PLANNED)**, link to guide/CLAUDE.md/security policy, a clear statement "pre-release: no inference code yet". No performance numbers.
- `CONTRIBUTING.md`: the §17 flow, Conventional Commit prefixes (feat/fix/docs/test/chore/ci), dev setup placeholder (`uv sync` once Task 4 merges), pre-commit gate checklist, a "Security: reporting accidental exposure" section pointing to `SECURITY.md`.
- `CODE_OF_CONDUCT.md`: Contributor Covenant 2.1 text fetched from the official source; enforcement contact = GitHub private reporting / maintainer profile (no personal email).
- `CHANGELOG.md`: Keep-a-Changelog format with an `## [Unreleased]` section.
- `.github/CODEOWNERS`: `* @vikalp1234`.
- PR template: summary, linked issue, acceptance criteria, tests run, **security checklist** (no secrets, scanner ran, docs/graphs updated).

- [ ] **Step 1: Branch**: `git switch -c phase0/community-files` (from updated `main`)
- [ ] **Step 2: Write the files per the decisions above.**
- [ ] **Step 3: Verify**: `grep -rn "PLANNED" README.md` shows the status table; `grep -rniE "@gmail|@outlook|password=|token=" README.md CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md` returns nothing.
- [ ] **Step 4: Commit** — `docs: add README, CONTRIBUTING, CoC, CHANGELOG, and GitHub templates`

---

### Task 4: uv backend skeleton (Python 3.12)

**Files:**
- Create: `backend/pyproject.toml`, `backend/.python-version` (content `3.12`), `backend/uv.lock` (generated), `backend/tests/test_smoke.py`, `backend/app/__init__.py`

**Interfaces — Produces:** a project that CI (Task 6) can run with `uv sync --frozen`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`.

**Decisions:**
- `pyproject.toml`: name `inferx-backend`, `requires-python = ">=3.12,<3.13"`, **no runtime dependencies yet** (FastAPI/torch arrive in v0.1.0 with justification), dev dependency group: `pytest`, `ruff`. Ruff config: line-length 100, `select = ["E","F","I","B","UP","S"]` (S = bandit-style security rules).
- No `domain/application/...` packages yet (CLAUDE.md §10.3: no empty layers).

- [ ] **Step 1: Branch**: `git switch -c phase0/backend-skeleton`

- [ ] **Step 2: Scaffold**

```bash
mkdir -p backend/app backend/tests && cd backend
uv python pin 3.12
uv init --bare --name inferx-backend
uv add --dev pytest ruff
```

Then edit `pyproject.toml` to add the `requires-python` pin and `[tool.ruff]` settings above.

- [ ] **Step 3: Write failing test first** — `backend/tests/test_smoke.py`:

```python
import sys


def test_python_is_3_12():
    assert sys.version_info[:2] == (3, 12)


def test_app_package_importable():
    import app  # noqa: F401
```

- [ ] **Step 4: Run to see it fail**

Run: `cd backend && uv run pytest -q`
Expected: FAIL on `import app` (package missing) before `app/__init__.py` exists.

- [ ] **Step 5: Create empty `backend/app/__init__.py`, re-run**

Run: `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`
Expected: `2 passed`; ruff clean.

- [ ] **Step 6: Commit** (include `uv.lock`; confirm it contains no credentials/index URLs with tokens: `grep -iE "token|password" backend/uv.lock` → nothing) — `chore: add uv backend skeleton with ruff and pytest`

---

### Task 5: pre-commit with Gitleaks

**Files:**
- Create: `.pre-commit-config.yaml`; optional `.gitleaks.toml` only if a documented false positive appears (none expected).

**Decisions:**
- Hooks: `gitleaks/gitleaks` (hook id `gitleaks`, pin `rev` to the tag matching `gitleaks version` from Task 0), `astral-sh/ruff-pre-commit` (`ruff`, `ruff-format`, pin `rev`), plus `pre-commit-hooks`: `check-added-large-files` (500 KB), `detect-private-key`, `check-merge-conflict`, `end-of-file-fixer`.
- Never use `--no-verify`.

- [ ] **Step 1: Branch**: `git switch -c phase0/precommit-gitleaks`
- [ ] **Step 2: Write `.pre-commit-config.yaml`; run `pre-commit install`.**
- [ ] **Step 3: Verify hook blocks a leak (in a scratch dir, never in this repo's history):**

```bash
S=$(mktemp -d) && cd "$S" && git init -q && cp "<repo>/.pre-commit-config.yaml" .
pre-commit install
T=$(python3 -c "import secrets,string;print('ghp_'+''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(36)))")
echo "github_token = \"$T\"" > leak.txt
git add leak.txt && git commit -m "test"
```

Expected: commit **fails** with a gitleaks `github-pat` finding. (Do not use AWS's documented `...EXAMPLE` keys: gitleaks allowlists them, so they pass.) Delete `$S` afterward. If it passes, the hook is mis-configured — fix before continuing.

- [ ] **Step 4: Verify clean tree passes**: `pre-commit run --all-files` → all Passed.
- [ ] **Step 5: Commit** — `ci: add pre-commit with gitleaks, ruff, and hygiene hooks`

---

### Task 6: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/ci.yml`

**Decisions (job names are the contract for Task 7):**
- Triggers: `pull_request` and `push` to `main`. Top-level `permissions: contents: read`.
- Job `secret-scan`: `actions/checkout` with `fetch-depth: 0`, `gitleaks/gitleaks-action@v2` (personal-account repos need no licence; org repos would).
- Job `backend`: `astral-sh/setup-uv`, `uv python install 3.12`, then in `backend/`: `uv sync --frozen`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q`.
- Pin third-party actions to a full release tag (SHA pinning preferred; record chosen versions in the PR). No secrets used; no `pull_request_target`.

- [ ] **Step 1: Branch**: `git switch -c phase0/ci-workflow`
- [ ] **Step 2: Write `ci.yml` per the decisions above.**
- [ ] **Step 3: Local sanity**: `python3 -c "import yaml,sys;yaml.safe_load(open('.github/workflows/ci.yml'))"` → no error.
- [ ] **Step 4: Commit, push branch (after maintainer OK), open PR.**

Run: `gh pr create --fill` then `gh pr checks --watch`
Expected: jobs `secret-scan` and `backend` both pass. If either fails, fix the root cause; do not weaken the check.

---

### Task 7: Repository settings and branch protection (maintainer-owned)

**Files:** none (GitHub settings). Use the UI or `gh api`; changing repo settings needs maintainer confirmation.

- [ ] **Step 1: Enable security features** — Settings → Code security: Private vulnerability reporting, Dependabot alerts + security updates, Secret scanning + push protection.
- [ ] **Step 2: Protect `main`** — require PR, 1 approving review (CODEOWNERS), required status checks **`secret-scan`** and **`backend`** (names must match Task 6), require branches up to date, block force-push and deletion. (Solo maintainer: you can't approve your own PR under strict rules; keep "do not allow bypass" off or add a second reviewer — decision for the maintainer.)
- [ ] **Step 3: Verify** — open a throwaway PR with a trivial change: checks gate the merge; direct `git push origin main` is rejected.
- [ ] **Step 4: Update status** — README status table remains PLANNED; add a CHANGELOG `[Unreleased]` entry "Phase 0 repository bootstrap".

---

## Self-review

- **Spec coverage:** guide §13 (secrets, CI scans, non-root n/a yet), §17 governance files (LICENSE exists, CONTRIBUTING, CoC, SECURITY, CHANGELOG, templates, branch protection) → Tasks 1–7. Docs §5 layout deliberately deferred (no empty layers). SBOM/container scanning: deferred to when containers exist (v1+).
- **Type/name consistency:** CI job names `secret-scan` / `backend` match across Tasks 6–7; `backend/` is the working dir in Tasks 4 and 6.
- **Proportion:** config-file contents are specified by decision, not transcribed.

## Exit criteria for Phase 0

CI green on `main` with `secret-scan` + `backend`; leak-block test demonstrated (Task 5 Step 3); branch protection verified (Task 7 Step 3); `uv sync` works from a fresh clone on Python 3.12; no phase beyond Phase 0 marked as started.
