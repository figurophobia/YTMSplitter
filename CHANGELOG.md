# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- Replaced the README banner with the plain pizza-sliced logo.
- Simplified the social preview to the same logo on a dark background.

## [1.2.0] - 2026-10-26

### Added

- `ytmsplitter labels`: export self-contained prompt batches and import JSON
  labels, so the AI engine can be used with opencode, Claude Code or any other
  assistant without an LLM API key.
- `labels --status`, `--batch-size`, `--dir` and `--overwrite` for managing the
  workflow.
- A generated `data/label_batches/README.md` with copy-paste commands for
  opencode and Claude Code.
- Documentation and FAQ for the external-assistant workflow.

### Changed

- The no-key error from `ytmsplitter ai` now points to the `labels` workflow
  instead of only suggesting an API.

## [1.1.0] - 2026-10-26

### Added

- `ytmsplitter quickstart`: authenticate, download Liked Music and classify in
  one command.
- `--browser` support for Firefox, Chrome, Chromium, Brave, Edge, Opera,
  Vivaldi, LibreWolf and Safari.
- `--yes` confirmation requirement for destructive `--delete-old-chips` runs.
- Logo, README banner and social preview assets.
- Contributing guide, security policy, changelog, issue forms, pull request
  template, Dependabot and linting in CI.

### Changed

- The project, CLI output, documentation and default playlist names are now in
  English.
- `--privacy` accepts lowercase values and normalises them.
- `doctor` reports Python, data directory, library, playlist and AI status.
- `ai` only creates an authenticated client when it actually needs one.
- `--delete-old-chips` also recognises the legacy `Me gusta · …` prefix.
- Improved error messages with actionable next steps.

### Fixed

- `--delete-old-chips` no longer proceeds without explicit confirmation.
- Existing playlists created with the old Spanish names keep working:
  `data/created_ai.json` keys are migrated automatically.

## [1.0.0] - 2026-10-16

### Added

- Initial release with the `chips` and `ai` engines, `auth`, `doctor`, `export`,
  idempotent playlist creation and `ai --update`.
