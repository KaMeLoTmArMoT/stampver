# Agent Handoff Guide (`HANDOFF.md`)

This document provides context for future AI coding agents working on or extending **`stampver`**.

---

## 🎯 Purpose & Core Invariants

`stampver` is a zero-config, universal versioning & build-stamping tool built for AI agents and developer Git pre-commit hooks.

### Non-Negotiable Requirements:
1. **Date Always**: Timestamp (`YYYY.MM.DD-HHMM`) is always included in resolved full versions.
2. **Optional SemVer**: SemVer (`1.12.3`) is used if detected in `version.txt`, `package.json`, `Cargo.toml`, or `pyproject.toml`, or if explicitly bumped via `--bump [patch|minor|major]`.
3. **64-Char Build Hash**: Computes SHA-256 HMAC `Version + Date + Commit + Salt` for binary anti-tampering and telemetry.
4. **Agent-First Interface**: Clean `--json` output flag on all commands.
5. **Git Pre-Commit Hook Integration**: `--stage` automatically runs `git add` on updated manifest files.

---

## 📂 Current Python Prototype Structure

* [`pyproject.toml`](file:///g:/programming/stampver/pyproject.toml): Package configuration with `stampver` entry point.
* [`stampver/core.py`](file:///g:/programming/stampver/stampver/core.py): Multi-manifest auto-detector & version resolver.
* [`stampver/cli.py`](file:///g:/programming/stampver/stampver/cli.py): CLI interface (`info`, `stamp`, `hook-install`).
* [`stampver/hooks.py`](file:///g:/programming/stampver/stampver/hooks.py): Git pre-commit installer.
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
