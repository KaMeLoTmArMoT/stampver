# `stampver`

Universal versioning and build stamping CLI tool designed for AI agents, developers, and Git pre-commit hooks.

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ⚡ Features

- 🎛️ **Config-Driven Formats**: per-repo `stampver.toml` chooses `semver` (`v1.2.3-2026.08.11-2057`), `semverrun` (CI run suffix), or `date` (`2026.08.11-2057`). Auto-detect remains the default.
- ⏱️ **Date Always**: timestamp is always included in full versions.
- 🔍 **Auto-Detector + Explicit Targets**: discovers `pyproject.toml`, `package.json`, `manifest.json`, `Cargo.toml`, `build_info.py`, `index.html` (`meta[name="version"]`, `?v=` cache busting), `build.gradle.kts`, `version.txt` — or takes explicit targets from config.
- 🔐 **64-Character Cryptographic Build Hash**: SHA-256 HMAC of `Version + Date + Git Commit + Salt`.
- 🪝 **Pre-Commit Framework Integration**: native `.pre-commit-hooks.yaml` support.
- 🤖 **AI Agent JSON Support**: `--json` outputs machine-parseable payloads.
- 🧬 **Legacy Templates**: `version.py` / `version.js` consumer templates (`VERSION`/`COMMIT_HASH`/`BUILD_DATE`/`FULL_VERSION`, `window.*`) for existing apps.

## 🎛️ Configuration (`stampver.toml`)

Place in the repository root to control the format and extra targets:

```toml
format = "semver"              # semver | semverrun | date (default: auto-detect)
salt = ""                      # HMAC salt for build hash
version_txt = "version.txt"    # false/omit-specific path; null to disable
pyproject = true               # default: true (date repos opt-in via toml)
build_info = ["server/build_info.py"]        # build_info.py template targets
version_py = ["app/version.py"]              # legacy version.py template targets
version_js = ["app/static/tma/version.js"]   # window.* module targets
version_ts = ["src/version.ts"]              # TypeScript targets
html_meta = ["UI/index.html"]                # <meta name="version"> targets
html_cache_bust = ["app/static/tma/index.html"]  # asset ?v= cache busting
cache_bust_regex = '(\.(?:css|js)\?v=)[^"\'\s>]+'  # override default regex
```

### Formats

| Format | Base in `version.txt` | Full version | Used by |
|---|---|---|---|
| `semver` | `0.18.0` | `v0.18.0-2026.08.26-1454` | GyroMouse, led_sync |
| `semverrun` | `0.18.0` | `v0.18.0-2026.08.26-1454-42` (run via `BUILD_RUN_NUMBER`) | GyroMouse CI |
| `date` | `2026.08.26-1454` | `2026.08.26-1454` | tg-gatekeeper, AWS_Project |

### Environment overrides (CI)

`BUILD_FULL_VERSION` > computed full version; `BUILD_TIMESTAMP` (`YYYY.MM.DD-HHMM`) > date; `BUILD_VERSION_BASE` > semver base; `BUILD_RUN_NUMBER` > appended in `semverrun` mode.

---

## 📦 Installation

### Option 1: Install from GitHub (Recommended)

Using `pip`:
```bash
pip install git+https://github.com/KaMeLoTmArMoT/stampver.git@v0.2.0
```

Using `uv` as a global tool:
```bash
uv tool install git+https://github.com/KaMeLoTmArMoT/stampver.git@v0.2.0
```

Using `uv` ad-hoc in CI:
```bash
uvx --from git+https://github.com/KaMeLoTmArMoT/stampver.git@v0.2.0 stampver stamp
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
    rev: v0.2.0
    hooks:
      - id: stampver
        args: [--stage]
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

### Inspect Resolved Version
```bash
stampver info --json
```

### CI Drift Gate (base consistency)
```bash
stampver check            # exit 1 on any base-version drift across files
stampver check --json
```
Compares stable bases only (`version.txt`, `pyproject.toml`, `package.json`, `manifest.json`, `Cargo.toml`, `__init__.py __version__`); date-bearing build artifacts are ignored, so it is safe in CI after every commit.

---

## Project layout

```text
stampver/
├── config.py    # stampver.toml loading (StampverConfig)
├── core.py      # version math: contexts, detection, hashing
├── engine.py    # target discovery + stamp_workspace orchestration
├── writers.py   # per-artifact writers (one class per template)
├── cli.py       # argparse interface (info / stamp / hook-install)
└── hooks.py     # git pre-commit hook installer
```

---



## License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
