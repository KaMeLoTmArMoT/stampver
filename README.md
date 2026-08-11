# `stampver`

Universal date-first versioning and build stamping CLI tool designed for AI agents, developers, and Git pre-commit hooks.

## Features
- **Date-Always Policy**: Version string always includes UTC timestamp (`2026.08.11-2057`). SemVer (`1.12.3`) is optional and updated if present.
- **Zero-Config Auto-Detector**: Automatically detects and stamps `package.json`, `manifest.json`, `Cargo.toml`, `pyproject.toml`, `build_info.py`, `index.html` (`meta[name="version"]`), `build.gradle.kts`, and `version.txt`.
- **64-Character Cryptographic Build Hash**: Computes SHA-256 HMAC hash of `Version + Date + Git Commit + Salt`.
- **Pre-Commit Staging**: `--stage` automatically `git add`s modified version manifests into the current commit.
- **AI Agent JSON Support**: `--json` outputs machine-parseable JSON payloads.

## Usage

### 1. Check Info
```bash
python -m stampver.cli info
# or if installed:
stampver info --json
```

### 2. Stamp Version
```bash
python -m stampver.cli stamp
# Bump patch:
python -m stampver.cli stamp --bump patch --stage
```

### 3. Install Pre-Commit Hook
```bash
python -m stampver.cli hook-install
```

## Directory Structure
```text
stampver/
├── pyproject.toml
├── README.md
├── rust_core/        # Reserved for future Rust port
│   └── README.md
└── stampver/
    ├── __init__.py
    ├── cli.py        # CLI interface (argparse, JSON output)
    ├── core.py       # Core stamping & auto-detection engine
    └── hooks.py      # Git pre-commit hook manager
```
