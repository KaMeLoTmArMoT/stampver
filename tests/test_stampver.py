import json

from stampver.core import bump_semver, generate_build_hash, resolve_context, stamp_workspace


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


def test_stamp_workspace(tmp_path):
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({"name": "test-pkg", "version": "1.0.0"}), encoding="utf-8")

    res = stamp_workspace(str(tmp_path), bump="minor")
    assert res.context.semver == "1.1.0"
    assert "package.json" in res.updated_files

    updated_pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
    assert updated_pkg["version"] == "1.1.0"
    assert "buildHash" in updated_pkg


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
