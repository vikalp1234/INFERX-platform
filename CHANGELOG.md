# Changelog

All notable changes are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning: [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-11-26

### Added
- Clean Architecture backend skeleton: domain (`ModelSpec`, `GenerationConfig`, results, errors), application (`ModelExecutionPort`, `LoadModel`, `TokenizePrompt`, `GenerateText`), settings, JSON logging, composition root.
- `TransformersInferenceAdapter` with a shared contract test suite (fake plus real model, real-model tests marked `model`).
- `GET /health` liveness endpoint and a CLI to load, tokenize and generate (exit codes 0/1/2).
- Import-boundary enforcement (import-linter) in CI.
- Docs: approved model notes, v0.1.0 component graph, verification evidence.

### Security
- Model revisions must be pinned 40-character SHAs; `trust_remote_code` is always off; prompts and generated text are never logged.

## Phase 0 — repository bootstrap (no release tag)

### Added
- Phase 0 repository bootstrap: ignore rules, governance and security docs, community files, uv backend skeleton, secret scanning and CI.
- Repository ruleset on `main`: pull request required, `secret-scan` and `backend` checks required, force pushes and deletions blocked.

### Fixed
- `.gitignore` now anchors the model-weights rules (`/models/`, `/backend/models/`) so a future `app/domain/models/` package is not ignored.
