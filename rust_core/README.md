# Future Rust Engine Port (`stampver-core`)

This directory is reserved for the native Rust port of `stampver`.

## Planned Architecture

When porting the Python prototype to Rust:
- **CLI Parsing**: `clap` crate (with derive macro)
- **Manifest Parsers**:
  - `serde_json` for `package.json` and `manifest.json`
  - `toml` / `toml_edit` for `Cargo.toml` and `pyproject.toml`
  - `regex` for custom file patterns (`build_info.py`, `index.html`, `build.gradle.kts`)
- **Crypto / Hashing**: `sha2` crate for 64-character SHA-256 build hash tokens
- **Subprocess**: `std::process::Command` for `git` interactions

## Dual Packaging Plan
1. **PyPI Wheel**: Built via `maturin` / `PyO3`
2. **NPM Package**: Built via `napi-rs` or native pre-compiled binary wrapper
3. **Standalone Binary**: `stampver.exe` (Windows) / `stampver` (Linux/macOS)
