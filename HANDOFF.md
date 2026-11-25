# Agent Handoff Guide (`HANDOFF.md`)

Context for AI agents working on `stampver` (config-driven versioning & build-stamping tool).

## Core Invariants
1. **Date Always**: `YYYY.MM.DD-HHMM` timestamp is always included in resolved full versions.
2. **Config Formats**: `stampver.toml` selects `semver` (`v1.2.3-...`), `semverrun` (run suffix), `date` (no semver), or `auto` (default).
3. **Date != SemVer**: `2026.08.26-1454` in `version.txt`/`pyproject.toml` must not be treated as a SemVer base.
4. **64-Char Build Hash**: SHA-256 HMAC `Version + Date + Commit + Salt` for anti-tampering and telemetry.
5. **Agent-First CLI**: `--json` output flag on all commands; `--stage` runs `git add` on updated manifests.
6. **CI Env Overrides**: `BUILD_FULL_VERSION` > computed full version; `BUILD_TIMESTAMP`, `BUILD_VERSION_BASE`, `BUILD_RUN_NUMBER` override respective inputs.

## Structure
- `pyproject.toml`: Package metadata (`stampver` entry point, Hatchling).
- `stampver.toml`: Self-stamp config (`format = "semver"`).
- `.pre-commit-hooks.yaml`: Pre-commit framework hook definitions.
- `stampver/config.py`: `StampverConfig` + `stampver.toml` loader.
- `stampver/core.py`: `VersionContext`, resolution, SemVer/date detection, hashing.
- `stampver/engine.py`: `stamp_workspace`, writer discovery, diff-aware writes.
- `stampver/writers.py`: Per-artifact writers (`build_info.py`, `version.py`, `version.js`, `package.json`, etc.).
- `stampver/cli.py`: CLI (`info`, `stamp`, `check`, `hook-install`).
- `stampver/hooks.py`: Git pre-commit installer.
- `scratch/IDEAS.md`: Future Rust engine port plan (`rust_core/`).

## Common Commands
```bash
python -m stampver.cli info --json
python -m stampver.cli stamp --stage
python -m stampver.cli stamp --bump patch --stage --json
python -m stampver.cli hook-install --dir /path/to/target/repo
```

## Config Quick Reference (`stampver.toml`)
```toml
format = "semver"            # semver | semverrun | date | auto
salt = ""
version_txt = "version.txt"  # null to disable
pyproject = true             # date repos opt-in
build_info = []              # build_info.py template paths
version_py = []              # legacy VERSION/COMMIT_HASH paths
version_js = []              # window.* paths
version_ts = []              # TS exports paths
html_meta = []               # <meta name="version"> + build-hash
html_cache_bust = []         # ?v= asset cache busting
cache_bust_regex = ''        # override default regex
```
