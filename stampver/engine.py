"""Stamping engine: discovers targets, renders writers, writes diff-aware."""

import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field

from stampver.config import StampverConfig
from stampver.core import VersionContext, looks_like_date, resolve_context
from stampver.writers import (
    BuildInfoPyWriter,
    CargoWriter,
    GradleWriter,
    HtmlWriter,
    InitPyWriter,
    ManifestJsonWriter,
    PackageJsonWriter,
    PyprojectWriter,
    VersionJsWriter,
    VersionPyWriter,
    VersionTsWriter,
    VersionTxtWriter,
    Writer,
)

logger = logging.getLogger("stampver")

_DEFAULT_BUILD_INFO_PATHS = (
    os.path.join("server", "build_info.py"),
    os.path.join("build_info.py"),
    os.path.join("_version.py"),
)
_DEFAULT_TS_PATHS = (
    os.path.join("src", "version.ts"),
    os.path.join("version.ts"),
    os.path.join("src", "buildInfo.ts"),
    os.path.join("buildInfo.ts"),
)
_SKIP_DIRS = {"node_modules", "build", "dist", "target", "venv", "__pycache__"}


@dataclass
class StampResult:
    context: VersionContext
    updated_files: list[str] = field(default_factory=list)
    staged_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def collect_writers(root_dir: str, config: StampverConfig, ctx: VersionContext) -> list[Writer]:
    """Discover stamp targets.

    Config (stampver.toml) adds explicit targets and controls the format; the
    discovery of established artifact files (package.json, manifest.json,
    build.gradle) keeps working in any mode.
    """
    has_explicit_targets = any(
        [
            config.build_info,
            config.version_py,
            config.version_js,
            config.version_ts,
            config.html_meta,
            config.html_cache_bust,
        ]
    )
    writers: list[Writer] = []

    # 1. version.txt - persists semver base or date stamp
    if config.version_txt is not None:
        txt_path = os.path.join(root_dir, config.version_txt)
        if ctx.semver or not has_explicit_targets or os.path.exists(txt_path):
            if config.version_txt is None:
                pass
            writers.append(VersionTxtWriter(txt_path))

    # 2. pyproject.toml [project] version
    pyproject_path = os.path.join(root_dir, "pyproject.toml")
    use_pyproject = os.path.isfile(pyproject_path)
    want_pyproject = ctx.semver if config.pyproject is None else config.pyproject
    if use_pyproject and want_pyproject:
        writers.append(PyprojectWriter(pyproject_path))

    # 3. package.json
    pkg_json = os.path.join(root_dir, "package.json")
    if os.path.isfile(pkg_json):
        writers.append(PackageJsonWriter(pkg_json))

    # 4. manifest.json (chrome extension / PWA)
    for m_path in (
        os.path.join(root_dir, "chrome_extension", "manifest.json"),
        os.path.join(root_dir, "manifest.json"),
    ):
        if os.path.isfile(m_path):
            writers.append(ManifestJsonWriter(m_path))

    # 5. Cargo.toml (semver repos)
    cargo_path = os.path.join(root_dir, "Cargo.toml")
    if os.path.isfile(cargo_path) and ctx.semver:
        writers.append(CargoWriter(cargo_path))

    # 6. build_info.py targets
    build_info_paths = (
        [os.path.join(root_dir, p) for p in config.build_info]
        if config.build_info
        else [os.path.join(root_dir, p) for p in _DEFAULT_BUILD_INFO_PATHS]
    )
    for b_path in build_info_paths:
        if os.path.exists(b_path):
            writers.append(BuildInfoPyWriter(b_path))

    # 7. version.py legacy targets (config-scoped)
    for v_path in config.version_py:
        writers.append(VersionPyWriter(os.path.join(root_dir, v_path)))

    # 8. __init__.py __version__ (semver repos only)
    if ctx.semver:
        for init_path in iter_files(root_dir, "__init__.py"):
            if has_assigned_init_version(init_path):
                writers.append(InitPyWriter(init_path))

    # 9. version.ts targets
    if config.version_ts:
        ts_paths = [os.path.join(root_dir, p) for p in config.version_ts]
    else:
        ts_paths = [
            os.path.join(root_dir, p)
            for p in _DEFAULT_TS_PATHS
            if os.path.exists(os.path.join(root_dir, p))
        ]
        if (
            not ts_paths
            and os.path.isdir(os.path.join(root_dir, "src"))
            and (
                os.path.isfile(pkg_json) or os.path.isfile(os.path.join(root_dir, "tsconfig.json"))
            )
        ):
            ts_paths = [os.path.join(root_dir, "src", "version.ts")]
    for t_path in ts_paths:
        if os.path.exists(t_path) or is_js_ts_project(root_dir):
            writers.append(VersionTsWriter(t_path))

    # 10. version.js legacy targets (config-scoped)
    for j_path in config.version_js:
        writers.append(VersionJsWriter(os.path.join(root_dir, j_path)))

    # 11. HTML meta tags + cache busting
    if config.html_meta or config.html_cache_bust:
        for meta_path in config.html_meta:
            full_path = os.path.join(root_dir, meta_path)
            if os.path.isfile(full_path):
                writers.append(HtmlWriter(full_path, meta=True))
        for cb_path in config.html_cache_bust:
            full_path = os.path.join(root_dir, cb_path)
            if os.path.isfile(full_path):
                writers.append(
                    HtmlWriter(
                        full_path,
                        meta=False,
                        cache_bust=True,
                        cache_bust_regex=config.cache_bust_regex,
                    )
                )
    elif not has_explicit_targets:
        for h_path in iter_files_with_meta(root_dir):
            writers.append(HtmlWriter(h_path, meta=True))

    # 12. Android gradle
    if config.gradle is not False:
        for g_path in (
            os.path.join(root_dir, "android", "app", "build.gradle.kts"),
            os.path.join(root_dir, "android", "app", "build.gradle"),
        ):
            if os.path.isfile(g_path):
                writers.append(GradleWriter(g_path))

    return writers


def consistency_issues(root_dir: str) -> list[str]:
    """Verify base version consistency across declaration files (drift gate).

    Date-bearing files (build_info DATE/FULL_VERSION, manifest version_name) are
    intentionally ignored - only the stable base version is compared.
    """
    issues: list[str] = []
    declared: tuple[str, str] | None = None

    def register(source: str, value: str | None) -> None:
        nonlocal declared
        if value is None or looks_like_date(value):
            return
        if declared is None:
            declared = (source, value)
        elif value != declared[1]:
            issues.append(f"{source}: {value!r} != {declared[0]}: {declared[1]!r}")

    txt_path = os.path.join(root_dir, "version.txt")
    if os.path.isfile(txt_path):
        line = read_file(txt_path).strip()
        register("version.txt", line)

    pyproject_path = os.path.join(root_dir, "pyproject.toml")
    if os.path.isfile(pyproject_path):
        m = re.search(r"\[project\][\s\S]*?(?=\n\[|\Z)", read_file(pyproject_path))
        if m:
            vm = re.search(r'^\s*version\s*=\s*"([^"]+)"', m.group(0), flags=re.MULTILINE)
            if vm:
                register("pyproject.toml", vm.group(1))

    for name in (
        "package.json",
        "manifest.json",
        os.path.join("chrome_extension", "manifest.json"),
    ):
        path = os.path.join(root_dir, name)
        if os.path.isfile(path):
            try:
                data = json.loads(read_file(path))
                if isinstance(data.get("version"), str):
                    register(name, data["version"])
            except (OSError, ValueError):
                pass

    cargo_path = os.path.join(root_dir, "Cargo.toml")
    if os.path.isfile(cargo_path):
        cm = re.search(r'\[package\][\s\S]*?\bversion\s*=\s*"([^"]+)"', read_file(cargo_path))
        if cm:
            register("Cargo.toml", cm.group(1))

    if declared:
        for init_path in iter_files(root_dir, "__init__.py"):
            if has_assigned_init_version(init_path):
                im = re.search(r'__version__\s*=\s*"([^"]+)"', read_file(init_path))
                if im:
                    register(init_path, im.group(1))

    return issues


def stamp_workspace(
    root_dir: str,
    config: StampverConfig | None = None,
    bump: str | None = None,
    salt: str = "",
    stage: bool = False,
    dry_run: bool = False,
) -> StampResult:
    config = config or StampverConfig.load(root_dir)
    effective_salt = salt if salt else config.salt
    ctx = resolve_context(root_dir, format_key=config.format, bump=bump, salt=effective_salt)
    updated_files: list[str] = []
    errors: list[str] = []

    for writer in collect_writers(root_dir, config, ctx):
        try:
            new_content = writer.render(ctx)
        except Exception as e:
            errors.append(f"Failed rendering {writer.path}: {e}")
            continue
        write_if_changed(writer.path, new_content, updated_files, errors, dry_run=dry_run)

    staged_files: list[str] = []
    if stage and updated_files and not dry_run:
        rel_files = [os.path.relpath(f, root_dir) for f in updated_files]
        try:
            subprocess.run(["git", "add"] + rel_files, cwd=root_dir, check=True)
            staged_files = rel_files
        except Exception as e:
            errors.append(f"Failed staging files in git: {e}")

    return StampResult(
        context=ctx,
        updated_files=[os.path.relpath(f, root_dir) for f in updated_files],
        staged_files=staged_files,
        errors=errors,
    )


def write_if_changed(
    target_path: str,
    new_content: str,
    updated_files: list[str],
    errors: list[str] | None = None,
    dry_run: bool = False,
):
    dir_name = os.path.dirname(target_path)
    if dir_name and not dry_run:
        os.makedirs(dir_name, exist_ok=True)

    if os.path.exists(target_path):
        try:
            with open(target_path, encoding="utf-8") as f:
                if f.read() == new_content:
                    return
        except Exception as e:
            msg = f"Error reading {target_path}: {e}"
            logger.debug(msg)
            if errors is not None:
                errors.append(msg)

    if dry_run:
        updated_files.append(target_path)
        return

    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        updated_files.append(target_path)
    except Exception as e:
        msg = f"Failed writing to {target_path}: {e}"
        logger.warning(msg)
        if errors is not None:
            errors.append(msg)


def iter_files(root_dir: str, suffix: str):
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in _SKIP_DIRS]
        for file in files:
            if suffix == "__init__.py":
                if file == "__init__.py":
                    yield os.path.join(root, file)
            elif file.endswith(suffix):
                yield os.path.join(root, file)


def iter_files_with_meta(root_dir: str):
    for path in iter_files(root_dir, ".html"):
        try:
            if '<meta name="version"' in read_file(path):
                yield path
        except OSError:
            continue


def has_assigned_init_version(init_path: str) -> bool:
    try:
        content = read_file(init_path)
    except OSError:
        return False
    return '__version__ = "' in content


def is_js_ts_project(root_dir: str) -> bool:
    return os.path.isfile(os.path.join(root_dir, "package.json")) or os.path.isfile(
        os.path.join(root_dir, "tsconfig.json")
    )


def read_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()
