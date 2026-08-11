import json

from stampver.core import bump_semver, generate_build_hash, resolve_context, stamp_workspace
from stampver.hooks import install_pre_commit_hook


def test_bump_semver():
    assert bump_semver("1.2.3", "patch") == "1.2.4"
    assert bump_semver("1.2.3", "minor") == "1.3.0"
    assert bump_semver("1.2.3", "major") == "2.0.0"


def test_generate_build_hash():
    h1 = generate_build_hash("1.0.0", "2026.08.11-2000", "a1b2c3d")
    h2 = generate_build_hash("1.0.0", "2026.08.11-2000", "a1b2c3d")
    h3 = generate_build_hash("1.0.0", "2026.08.11-2000", "a1b2c3d", salt="secret")
    assert len(h1) == 64
    assert h1 == h2
    assert h1 != h3


def test_resolve_context(tmp_path):
    (tmp_path / "version.txt").write_text("0.17.0\n", encoding="utf-8")
    ctx = resolve_context(str(tmp_path))
    assert ctx.semver == "0.17.0"
    assert "0.17.0" in ctx.full_version
    # Calver code should fit in 32-bit int
    assert int(ctx.calver_code) < 2147483647


def test_stamp_workspace(tmp_path):
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({"name": "test-pkg", "version": "1.0.0"}), encoding="utf-8")

    res = stamp_workspace(str(tmp_path), bump="minor")
    assert res.context.semver == "1.1.0"
    assert "package.json" in res.updated_files

    updated_pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
    assert updated_pkg["version"] == "1.1.0"
    assert "buildHash" in updated_pkg


def test_ts_version_stamping(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    ts_file = src_dir / "version.ts"
    ts_file.write_text("// dummy", encoding="utf-8")

    res = stamp_workspace(str(tmp_path), bump="patch")
    assert "src/version.ts" in [f.replace("\\", "/") for f in res.updated_files]
    content = ts_file.read_text(encoding="utf-8")
    assert "export const VERSION" in content
    assert "export const BUILD_HASH" in content


def test_ts_auto_creation(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"name": "auto-ts"}), encoding="utf-8")
    (tmp_path / "src").mkdir()

    res = stamp_workspace(str(tmp_path))
    assert "src/version.ts" in [f.replace("\\", "/") for f in res.updated_files]
    created_ts = (tmp_path / "src" / "version.ts").read_text(encoding="utf-8")
    assert "export const VERSION" in created_ts


def test_pyproject_toml_scoping(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    content = """[tool.other]
version = "9.9.9"

[project]
name = "my-proj"
version = "0.5.0"
"""
    pyproject.write_text(content, encoding="utf-8")

    res = stamp_workspace(str(tmp_path), bump="patch")
    assert res.context.semver == "0.5.1"
    new_text = pyproject.read_text(encoding="utf-8")
    assert 'version = "9.9.9"' in new_text
    assert 'version = "0.5.1"' in new_text


def test_dry_run(tmp_path):
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({"name": "dry-pkg", "version": "1.0.0"}), encoding="utf-8")

    res = stamp_workspace(str(tmp_path), bump="patch", dry_run=True)
    assert res.context.semver == "1.0.1"
    assert "package.json" in res.updated_files
    # File on disk must NOT be modified
    assert json.loads(pkg_json.read_text(encoding="utf-8"))["version"] == "1.0.0"


def test_pre_commit_backup(tmp_path):
    git_dir = tmp_path / ".git" / "hooks"
    git_dir.mkdir(parents=True)
    existing_hook = git_dir / "pre-commit"
    existing_hook.write_text("#!/bin/sh\necho custom\n", encoding="utf-8")

    ok, msg = install_pre_commit_hook(str(tmp_path))
    assert ok
    assert "backed up" in msg
    assert (git_dir / "pre-commit.bak").read_text(encoding="utf-8") == "#!/bin/sh\necho custom\n"


def test_python_init_stamping(tmp_path):
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    init_file = pkg_dir / "__init__.py"
    init_file.write_text('__version__ = "0.1.0"\n', encoding="utf-8")
    (tmp_path / "version.txt").write_text("0.1.0\n", encoding="utf-8")

    res = stamp_workspace(str(tmp_path), bump="minor")
    assert res.context.semver == "0.2.0"
    assert '__version__ = "0.2.0"' in init_file.read_text(encoding="utf-8")


def test_cli_version(capsys):
    import sys
    from unittest.mock import patch

    from stampver import __version__
    from stampver.cli import main

    with patch.object(sys, "argv", ["stampver", "-v"]):
        try:
            main()
        except SystemExit as e:
            assert e.code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out or __version__ in captured.err

