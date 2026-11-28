# Changelog

All notable changes are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning: [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-11-28

### Added
- Sampling controls in `GenerationConfig`: `temperature` (0 = greedy), `top_k`, `top_p`, `repetition_penalty`, `seed`; invalid or contradictory combinations are rejected.
- `GenerationTimings` (TTFT, TPOT, decode TPS, total, raw per-token stamps) captured by the Transformers adapter with documented measurement boundaries.
- Derived KV-cache size estimate (`ModelArchitecture`, `estimate_kv_cache`, `EstimateKvCache`), labelled `derived_from_model_config`.
- CLI flags `--temperature --top-k --top-p --repetition-penalty --seed --metrics`; metrics JSON on stderr with a provenance label per value.
- Docs: inference mechanics, v0.2.0 component graph, verification evidence; an output-free notebook.

### Changed
- `ModelExecutionPort` gained `architecture()`; `generate()` results carry `timings`. Log allowlist gained numeric timing fields (still no prompt or response text).

### Notes
- Stop sequences, HTTP endpoints and percentile reporting are out of scope (v1.2.x, v0.3.0, v2.0.0).

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
