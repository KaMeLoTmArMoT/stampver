# AGENTS.md

`stampver` - universal versioning and build-stamping CLI for AI agents, developers, and Git pre-commit hooks. Per-repo `stampver.toml` selects `semver` / `semverrun` / `date` formats; auto-detects `pyproject.toml`, `package.json`, `manifest.json`, `Cargo.toml`, `build_info.py`, `index.html`, `build.gradle.kts`, `version.txt`.

## Commands

| Task | Command |
|---|---|
| Install (editable) | `pip install -e .` |
| Run CLI | `stampver --help` / `stampver stamp [--stage] [--only-if-staged] [--force] [--json]` / `stampver check [--json]` |
| Run tests | `pytest` |
| Lint check & fix | `ruff check --fix` |
| Format | `ruff format` |

## Conventions

- Python `>=3.11`; hatchling build; console script entry point in `[project.scripts]`.
- Dogfooding: this repo stamps its own version - keep `.pre-commit-hooks.yaml`, `stampver.toml` and self-stamping consistent.
- Pre-commit hooks: `.pre-commit-hooks.yaml` provides `stampver` (smart stamp & stage; skips when git index is clean) and `stampver-check` (read-only drift consistency check; safe for CI pipelines).
- Formats: `date` (`2026.08.11-2057`), `semver` (`v0.18.0-2026.08.11-2057`), `semverrun` (appends CI run number). A date string is never parsed as SemVer.
- Legacy templates (`version.py`/`version.js` with `VERSION`/`COMMIT_HASH`/`BUILD_DATE`/`FULL_VERSION`) are locked; do not change without updating tests.
- 64-char build hash = SHA-256 HMAC(Version+Date+Commit+Salt); treat salt handling as security-sensitive.
