# Ideas & Future Plans

## Future Rust Engine Port (`stampver-core`)

Reserved directory: `rust_core/`.

### Planned Architecture
- **CLI**: `clap` (derive)
- **Manifest parsers**: `serde_json` (`package.json`, `manifest.json`), `toml` / `toml_edit` (`Cargo.toml`, `pyproject.toml`), `regex` (`build_info.py`, `index.html`, `build.gradle.kts`)
- **Crypto / Hashing**: `sha2` (64-char SHA-256 build hash tokens)
- **Subprocess**: `std::process::Command` for `git`

### Dual Packaging Plan
1. **PyPI Wheel**: `maturin` / `PyO3`
2. **NPM Package**: `napi-rs` or native binary wrapper
3. **Standalone Binary**: `stampver.exe` (Windows) / `stampver` (Linux/macOS)
