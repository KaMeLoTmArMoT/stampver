# Agent Handoff Guide (`HANDOFF.md`)

This document provides context for future AI coding agents working on or extending **`stampver`**.

---

## 🎯 Purpose & Core Invariants

`stampver` is a config-driven, universal versioning & build-stamping tool built for AI agents and developer Git pre-commit hooks.

### Non-Negotiable Requirements:
1. **Date Always**: Timestamp (`YYYY.MM.DD-HHMM`) is always included in resolved full versions.
2. **Config Formats**: `stampver.toml` selects `semver` (`v1.2.3-...`), `semverrun` (run suffix), or `date` (no semver); `auto` (auto-detect) defaults.
3. **A date string is never SemVer**: `2026.08.26-1454` in `version.txt`/`pyproject.toml` must not be treated as a SemVer base.
4. **64-Char Build Hash**: SHA-256 HMAC `Version + Date + Commit + Salt` for binary anti-tampering and telemetry.
5. **Agent-First Interface**: Clean `--json` output flag on all commands.
6. **Git Pre-Commit Hook Integration**: `--stage` runs `git add` on updated manifest files.
7. **Environment Overrides (CI)**: `BUILD_FULL_VERSION` > computed full version; `BUILD_TIMESTAMP`, `BUILD_VERSION_BASE`, `BUILD_RUN_NUMBER` override respective inputs.

---

## 📂 Structure

* [`pyproject.toml`](file:///g:/programming/stampver/pyproject.toml): Package configuration with `stampver` entry point.
* [`stampver/config.py`](file:///g:/programming/stampver/stampver/config.py): `StampverConfig` + `stampver.toml` loader.
* [`stampver/core.py`](file:///g:/programming/stampver/stampver/core.py): Version math - `VersionContext`, resolution, SemVer/date detection, hashing.
* [`stampver/engine.py`](file:///g:/programming/stampver/stampver/engine.py): `stamp_workspace`, writer discovery, diff-aware writes.
* [`stampver/writers.py`](file:///g:/programming/stampver/stampver/writers.py): One writer class per artifact (build_info.py, version.py, version.js, package.json, etc.).
* [`stampver/cli.py`](file:///g:/programming/stampver/stampver/cli.py): CLI interface (`info`, `stamp`, `hook-install`).
* [`stampver/hooks.py`](file:///g:/programming/stampver/stampver/hooks.py): Git pre-commit installer.
* [`stampver.toml`](file:///g:/programming/stampver/stampver.toml): Self-stamp config (dogfooding).
* [`rust_core/README.md`](file:///g:/programming/stampver/rust_core/README.md): Architecture plan for future Rust engine port.

---

## 🚀 Common Command Snippets

```bash
# Get JSON info for current workspace
python -m stampver.cli info --json

# Stamp current workspace and stage changes in Git
python -m stampver.cli stamp --stage

# Bump patch version and output JSON
python -m stampver.cli stamp --bump patch --stage --json

# Install pre-commit hook into target repo
python -m stampver.cli hook-install --dir /path/to/target/repo
```

---

## 🎛️ Config Quick Reference

```toml
format = "semver"            # semver | semverrun | date | auto
salt = ""
version_txt = "version.txt"  #  null to disable
pyproject = true             # date repos opt-in
build_info = []              # build_info.py template paths
version_py = []              # legacy VERSION/COMMIT_HASH template paths
version_js = []              # window.* template paths
version_ts = []              # TS exports template paths
html_meta = []               # <meta name="version"> + build-hash
html_cache_bust = []         # ?v= asset cache busting
cache_bust_regex = ''        # override default regex
```

---

## 🛠️ Project Structure

```text
stampver/
├── .pre-commit-hooks.yaml  # Hook definitions for pre-commit framework
├── pyproject.toml          # Hatchling package metadata
├── stampver.toml           # dogfooding config (format = "semver")
├── README.md               # Documentation
├── rust_core/              # Reserved for Rust engine port
└── stampver/
    ├── __init__.py         # Package entry & __version__
    ├── cli.py              # CLI parser (-v, stamp, info, hook-install)
    ├── config.py           # stampver.toml loading
    ├── core.py             # Version math, detection & hashing
    ├── engine.py           # stamp_workspace + discovery
    ├── writers.py          # Per-artifact writer classes
    └── hooks.py            # Pre-commit hook generator
```
