# Changelog

All notable changes are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning: [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Phase 0 repository bootstrap: ignore rules, governance and security docs, community files, uv backend skeleton, secret scanning and CI.
- Repository ruleset on `main`: pull request required, `secret-scan` and `backend` checks required, force pushes and deletions blocked.

### Fixed
- `.gitignore` now anchors the model-weights rules (`/models/`, `/backend/models/`) so a future `app/domain/models/` package is not ignored.
