import json

from stampver.config import StampverConfig
from stampver.core import (
    bump_semver,
    detect_semver,
    generate_build_hash,
    looks_like_date,
    resolve_context,
)
from stampver.engine import consistency_issues, stamp_workspace
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


def test_looks_like_date():
    assert looks_like_date("2026.08.26-1454") is True
    assert looks_like_date("2026.08.26") is True
    assert looks_like_date("0.18.0") is False
    assert looks_like_date("1.2.3") is False


def test_date_not_detected_as_semver(tmp_path):
    (tmp_path / "version.txt").write_text("2026.08.26-1454\n", encoding="utf-8")
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "date-proj"\nversion = "2026.08.26-1454"\n', encoding="utf-8"
    )
    assert detect_semver(str(tmp_path)) is None
    ctx = resolve_context(str(tmp_path))
    assert ctx.semver is None
    assert ctx.full_version == ctx.date_str
    assert "-2026." not in ctx.full_version


def test_resolve_context(tmp_path):
    (tmp_path / "version.txt").write_text("0.17.0\n", encoding="utf-8")
    ctx = resolve_context(str(tmp_path))
    assert ctx.semver == "0.17.0"
    assert "0.17.0" in ctx.full_version
    # Calver code should fit in 32-bit int
    assert int(ctx.calver_code) < 2147483647


def test_env_override_full_version(tmp_path):
    (tmp_path / "version.txt").write_text("0.18.0\n", encoding="utf-8")
    env = {
        "BUILD_FULL_VERSION": "v0.18.0-2026.08.26-1454-123",
        "BUILD_TIMESTAMP": "2026.08.26-1454",
    }
    ctx = resolve_context(str(tmp_path), env=env)
    assert ctx.full_version == "v0.18.0-2026.08.26-1454-123"
    assert ctx.date_str == "2026.08.26-1454"
    assert int(ctx.calver_code) == 2026082614


def test_semverrun_format(tmp_path):
    import os

    (tmp_path / "version.txt").write_text("0.18.0\n", encoding="utf-8")
    from contextlib import suppress

    os.environ["BUILD_RUN_NUMBER"] = "42"
    try:
        ctx = resolve_context(str(tmp_path), format_key="semverrun", env=os.environ)
        assert ctx.full_version.endswith("-42")
    finally:
        with suppress(KeyError):
            del os.environ["BUILD_RUN_NUMBER"]


def test_legacy_version_py_writer(tmp_path):
    (tmp_path / "version.txt").write_text("0.1.0\n", encoding="utf-8")
    cfg = StampverConfig(version_py=["app/version.py"])
    stamp_workspace(str(tmp_path), config=cfg)
    content = (tmp_path / "app" / "version.py").read_text(encoding="utf-8")
    assert 'VERSION = "0.1.0"' in content
    assert 'COMMIT_HASH = "unknown"' in content
    assert "BUILD_DATE" in content
    assert '__all__ = ["VERSION", "COMMIT_HASH", "BUILD_DATE", "FULL_VERSION"]' in content


def test_version_js_writer(tmp_path):
    (tmp_path / "version.txt").write_text("0.1.0\n", encoding="utf-8")
    cfg = StampverConfig(version_js=["app/static/version.js"])
    stamp_workspace(str(tmp_path), config=cfg)
    content = (tmp_path / "app" / "static" / "version.js").read_text(encoding="utf-8")
    assert 'window.APP_VERSION = "0.1.0";' in content
    assert "window.COMMIT_HASH" in content
    assert "window.FULL_VERSION" in content


def test_html_cache_bust(tmp_path):
    (tmp_path / "version.txt").write_text("0.1.0\n", encoding="utf-8")
    index = tmp_path / "tma" / "index.html"
    index.parent.mkdir()
    index.write_text('<link href="app.js?v=1.2.3">', encoding="utf-8")
    cfg = StampverConfig(html_cache_bust=["tma/index.html"])
    stamp_workspace(str(tmp_path), config=cfg)
    updated = (tmp_path / "tma" / "index.html").read_text(encoding="utf-8")
    assert "app.js?v=0.1.0" in updated


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


def test_date_format_stamps_pyproject(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "date-proj"\nversion = "2026.01.01-0000"\n', encoding="utf-8"
    )
    cfg = StampverConfig(format="date", pyproject=True)
    res = stamp_workspace(str(tmp_path), config=cfg)
    new_text = pyproject.read_text(encoding="utf-8")
    assert res.context.full_version == res.context.date_str
    assert f'version = "{res.context.date_str}"' in new_text


def test_config_loading(tmp_path):
    tmp_path.joinpath("stampver.toml").write_text("[format]\n", encoding="utf-8") if False else None
    (tmp_path / "stampver.toml").write_text(
        'format = "date"\n'
        'version_py = ["app/version.py"]\n'
        'version_js = ["app/static/version.js"]\n'
        'html_cache_bust = ["app/static/index.html"]\n',
        encoding="utf-8",
    )
    cfg = StampverConfig.load(str(tmp_path))
    assert cfg.format == "date"
    assert cfg.version_py == ["app/version.py"]
    assert cfg.version_js == ["app/static/version.js"]
    assert cfg.html_cache_bust == ["app/static/index.html"]


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


def test_consistency_check_consistent(tmp_path):
    (tmp_path / "version.txt").write_text("0.1.0\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "p"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    assert consistency_issues(str(tmp_path)) == []


def test_consistency_check_detects_drift(tmp_path):
    (tmp_path / "version.txt").write_text("0.1.0\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "p"\nversion = "0.2.0"\n', encoding="utf-8"
    )
    issues = consistency_issues(str(tmp_path))
    assert len(issues) == 1
    assert "pyproject.toml" in issues[0]


def test_consistency_check_ignores_dates(tmp_path):
    (tmp_path / "version.txt").write_text("2026.08.26-1454\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "p"\nversion = "2026.08.26-1454"\n', encoding="utf-8"
    )
    assert consistency_issues(str(tmp_path)) == []


def test_consistency_check_manifest(tmp_path):
    (tmp_path / "version.txt").write_text("1.0.0\n", encoding="utf-8")
    (tmp_path / "manifest.json").write_text(
        json.dumps({"version": "1.0.0", "version_name": "v1.0.0-2026.08.26-1454"}),
        encoding="utf-8",
    )
    assert consistency_issues(str(tmp_path)) == []


def test_cli_check_exit_code(tmp_path, capsys):
    import sys
    from unittest.mock import patch

    (tmp_path / "version.txt").write_text("0.1.0\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "p"\nversion = "0.1.0"\n', encoding="utf-8"
    )

    from stampver.cli import main

    with patch.object(sys, "argv", ["stampver", "check", "--dir", str(tmp_path)]):
        try:
            main()
        except SystemExit as e:
            assert e.code == 0
    assert "consistent" in capsys.readouterr().out

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "p"\nversion = "0.9.9"\n', encoding="utf-8"
    )
    with patch.object(sys, "argv", ["stampver", "check", "--dir", str(tmp_path)]):
        try:
            main()
        except SystemExit as e:
            assert e.code == 1


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


def test_pre_commit_hooks_yaml():
    import yaml

    with open(".pre-commit-hooks.yaml", encoding="utf-8") as f:
        hooks = yaml.safe_load(f)
    hook_ids = {h["id"]: h for h in hooks}
    assert "stampver" in hook_ids
    assert "stampver-check" in hook_ids
    assert hook_ids["stampver-check"]["entry"] == "stampver check"
    assert hook_ids["stampver"]["entry"] == "stampver stamp --stage"


def test_smart_stamp_skips_when_git_clean(tmp_path):
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True)

    (tmp_path / "version.txt").write_text("0.1.0\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("print(1)\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True)

    # 1. Clean git index: stamp_workspace with stage=True should skip
    res = stamp_workspace(str(tmp_path), stage=True)
    assert res.skipped is True
    assert "Clean git index" in res.skip_reason
    assert res.updated_files == []

    # 2. Stage real code change with build_info: stamp_workspace should stamp and stage
    (tmp_path / "build_info.py").write_text("# initial\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("print(2)\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py", "build_info.py"], cwd=tmp_path, check=True)
    res2 = stamp_workspace(str(tmp_path), stage=True)
    assert res2.skipped is False
    assert "build_info.py" in res2.updated_files
    assert "build_info.py" in res2.staged_files

    # 3. Explicit bump overrides clean git check
    subprocess.run(["git", "commit", "-m", "update"], cwd=tmp_path, check=True)
    res3 = stamp_workspace(str(tmp_path), stage=True, bump="minor")
    assert res3.skipped is False
    assert res3.context.semver == "0.2.0"
    assert "version.txt" in res3.updated_files


def test_smart_stamp_detects_drift_even_when_clean(tmp_path):
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True)

    (tmp_path / "version.txt").write_text("0.1.0\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "p"\nversion = "0.2.0"\n', encoding="utf-8"
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True)

    # Drift exists -> should not skip, should stamp
    res = stamp_workspace(str(tmp_path), stage=True)
    assert res.skipped is False
    assert len(res.updated_files) > 0


def test_cli_stamp_only_if_staged_json(tmp_path, capsys):
    import subprocess
    import sys
    from unittest.mock import patch

    from stampver.cli import main

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True)

    (tmp_path / "version.txt").write_text("0.1.0\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True)

    with patch.object(
        sys,
        "argv",
        ["stampver", "stamp", "--dir", str(tmp_path), "--only-if-staged", "--json"],
    ):
        main()
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "skipped"
    assert "Clean git index" in out["reason"]
