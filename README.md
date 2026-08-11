# `stampver`

Universal date-first versioning and build stamping CLI tool designed for AI agents, developers, and Git pre-commit hooks.

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ⚡ Features

- ⏱️ **Date-Always Policy**: Version string always includes UTC timestamp (`2026.08.11-2057`). SemVer (`1.12.3`) is preserved and bumped if present (`v1.12.3-2026.08.11-2057`).
- 🔍 **Zero-Config Auto-Detector**: Automatically detects and updates `pyproject.toml`, `package.json`, `manifest.json`, `Cargo.toml`, `build_info.py`, `index.html` (`meta[name="version"]`), `build.gradle.kts`, and `version.txt`.
- 🔐 **64-Character Cryptographic Build Hash**: Computes SHA-256 HMAC hash of `Version + Date + Git Commit + Salt`.
- 🪝 **Pre-Commit Framework Integration**: Native `.pre-commit-hooks.yaml` support for official pre-commit workflow.
- 🤖 **AI Agent JSON Support**: `--json` outputs machine-parseable JSON payloads for automated pipelines.

---

## 📦 Installation

### Option 1: Install from GitHub (Recommended)

Using `pip`:
```bash
pip install git+https://github.com/KaMeLoTmArMoT/stampver.git
```

Using `uv` as a global tool:
```bash
uv tool install git+https://github.com/KaMeLoTmArMoT/stampver.git
```

### Option 2: Manual Git Build & Local Install

```bash
git clone https://github.com/KaMeLoTmArMoT/stampver.git
cd stampver

# Install locally in editable mode with uv:
uv pip install -e .

# Or build wheel package manually:
uv build
pip install dist/*.whl
```

---

## 🪝 Pre-Commit Integration

### Using `pre-commit` Framework

Add `stampver` to your project's `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/KaMeLoTmArMoT/stampver
    rev: main  # or target release tag
    hooks:
      - id: stampver
```

### Or Install Native Git Hook (Zero External Dependencies)

Inside any target Git repository:

```bash
stampver hook-install
```

This installs `.git/hooks/pre-commit`, running `stampver stamp --stage` before every commit.

---

## 🚀 CLI Usage

### Check CLI Version
```bash
stampver -v
# Output: stampver 0.1.0
```

### Inspect Version Info
```bash
stampver info
stampver info --json
```

### Stamp Project Files
```bash
# Stamp current version & build hash:
stampver stamp

# Dry-run mode (preview updates without writing files):
stampver stamp --dry-run

# Stamp and bump SemVer (patch, minor, or major):
stampver stamp --bump patch --stage
```
