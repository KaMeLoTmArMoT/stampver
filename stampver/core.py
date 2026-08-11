import datetime
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass, field


@dataclass
class VersionContext:
    date_str: str  # e.g. "2026.08.11-2057"
    calver_code: str  # e.g. "20260811"
    commit_hash: str  # e.g. "a1b2c3d"
    semver: str | None  # e.g. "1.12.3" or None
    full_version: str  # e.g. "v1.12.3-2026.08.11-2057"
    build_hash: str  # 64-char SHA-256 token


@dataclass
class StampResult:
    context: VersionContext
    updated_files: list[str] = field(default_factory=list)
    staged_files: list[str] = field(default_factory=list)


def get_git_commit(root_dir: str) -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=root_dir,
        )
        return res.stdout.strip() if res.returncode == 0 and res.stdout.strip() else "unknown"
    except Exception:
        return "unknown"


def generate_build_hash(version_str: str, date_str: str, commit_hash: str, salt: str = "") -> str:
    raw_payload = f"{version_str}:{date_str}:{commit_hash}:{salt}".encode()
    return hashlib.sha256(raw_payload).hexdigest()


def bump_semver(semver_str: str, bump_type: str) -> str:
    parts = semver_str.strip().lstrip("v").split(".")
    if len(parts) < 3:
        while len(parts) < 3:
            parts.append("0")
    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return semver_str

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1

    return f"{major}.{minor}.{patch}"


def detect_semver(root_dir: str) -> str | None:
    # 1. Check version.txt
    version_txt = os.path.join(root_dir, "version.txt")
    if os.path.isfile(version_txt):
        with open(version_txt, encoding="utf-8") as f:
            line = f.readline().strip()
            if line and re.match(r"^v?\d+\.\d+(\.\d+)?", line):
                return line.lstrip("v")

    # 2. Check package.json
    pkg_json = os.path.join(root_dir, "package.json")
    if os.path.isfile(pkg_json):
        try:
            with open(pkg_json, encoding="utf-8") as f:
                data = json.load(f)
                if "version" in data and isinstance(data["version"], str):
                    return data["version"].lstrip("v")
        except Exception:
            pass

    # 3. Check Cargo.toml
    cargo_toml = os.path.join(root_dir, "Cargo.toml")
    if os.path.isfile(cargo_toml):
        try:
            with open(cargo_toml, encoding="utf-8") as f:
                content = f.read()
                m = re.search(r'\[package\][\s\S]*?version\s*=\s*"([^"]+)"', content)
                if m:
                    return m.group(1).lstrip("v")
        except Exception:
            pass

    # 4. Check pyproject.toml
    pyproject_toml = os.path.join(root_dir, "pyproject.toml")
    if os.path.isfile(pyproject_toml):
        try:
            with open(pyproject_toml, encoding="utf-8") as f:
                content = f.read()
                m = re.search(r'version\s*=\s*"([^"]+)"', content)
                if m:
                    return m.group(1).lstrip("v")
        except Exception:
            pass

    return None


def resolve_context(root_dir: str, bump: str | None = None, salt: str = "") -> VersionContext:
    now_utc = datetime.datetime.now(datetime.UTC)
    date_str = now_utc.strftime("%Y.%m.%d-%H%M")
    calver_code = now_utc.strftime("%Y%m%d")
    commit_hash = get_git_commit(root_dir)

    semver = detect_semver(root_dir)
    if bump and semver:
        semver = bump_semver(semver, bump)
    elif bump and not semver:
        semver = bump_semver("0.1.0", bump)

    if semver:
        full_version = f"v{semver}-{date_str}"
        base_version = semver
    else:
        full_version = f"v{date_str}"
        base_version = date_str

    build_hash = generate_build_hash(base_version, date_str, commit_hash, salt)

    return VersionContext(
        date_str=date_str,
        calver_code=calver_code,
        commit_hash=commit_hash,
        semver=semver,
        full_version=full_version,
        build_hash=build_hash,
    )


def stamp_workspace(
    root_dir: str, bump: str | None = None, salt: str = "", stage: bool = False
) -> StampResult:
    ctx = resolve_context(root_dir, bump=bump, salt=salt)
    updated_files: list[str] = []

    # 1. Update version.txt if present or if semver exists
    version_txt_path = os.path.join(root_dir, "version.txt")
    if ctx.semver or os.path.exists(version_txt_path):
        content = (ctx.semver if ctx.semver else ctx.date_str) + "\n"
        _write_if_changed(version_txt_path, content, updated_files)

    # 2. Update package.json
    pkg_json_path = os.path.join(root_dir, "package.json")
    if os.path.isfile(pkg_json_path):
        try:
            with open(pkg_json_path, encoding="utf-8") as f:
                data = json.load(f)
            if ctx.semver:
                data["version"] = ctx.semver
            data["buildDate"] = ctx.date_str
            data["buildHash"] = ctx.build_hash
            new_content = json.dumps(data, indent=2) + "\n"
            _write_if_changed(pkg_json_path, new_content, updated_files)
        except Exception:
            pass

    # 3. Update manifest.json (Chrome Extension / PWA)
    manifest_paths = [
        os.path.join(root_dir, "chrome_extension", "manifest.json"),
        os.path.join(root_dir, "manifest.json"),
    ]
    for m_path in manifest_paths:
        if os.path.isfile(m_path):
            try:
                with open(m_path, encoding="utf-8") as f:
                    manifest = json.load(f)
                if ctx.semver:
                    manifest["version"] = ctx.semver
                manifest["version_name"] = ctx.full_version
                new_content = json.dumps(manifest, indent=2) + "\n"
                _write_if_changed(m_path, new_content, updated_files)
            except Exception:
                pass

    # 4. Update pyproject.toml
    pyproject_path = os.path.join(root_dir, "pyproject.toml")
    if os.path.isfile(pyproject_path) and ctx.semver:
        try:
            with open(pyproject_path, encoding="utf-8") as f:
                content = f.read()
            new_content = re.sub(
                r'^(version\s*=\s*)"[^"]+"',
                f'\\1"{ctx.semver}"',
                content,
                flags=re.MULTILINE,
            )
            _write_if_changed(pyproject_path, new_content, updated_files)
        except Exception:
            pass

    # 5. Update Cargo.toml
    cargo_path = os.path.join(root_dir, "Cargo.toml")
    if os.path.isfile(cargo_path) and ctx.semver:
        try:
            with open(cargo_path, encoding="utf-8") as f:
                content = f.read()
            new_content = re.sub(
                r'(\[package\][\s\S]*?\bversion\s*=\s*)"[^"]+"',
                f'\\1"{ctx.semver}"',
                content,
                count=1,
            )
            _write_if_changed(cargo_path, new_content, updated_files)
        except Exception:
            pass

    # 6. Update Python build_info.py / _version.py
    python_info_paths = [
        os.path.join(root_dir, "server", "build_info.py"),
        os.path.join(root_dir, "build_info.py"),
        os.path.join(root_dir, "_version.py"),
    ]
    build_info_content = f'''"""
Auto-generated static build metadata.
Updated by stampver. Do not edit manually.
"""

VERSION = "{ctx.semver or ctx.date_str}"
COMMIT = "{ctx.commit_hash}"
DATE = "{ctx.date_str}"
FULL_VERSION = "{ctx.full_version}"
BUILD_HASH = "{ctx.build_hash}"
'''
    for py_path in python_info_paths:
        if os.path.exists(py_path):
            _write_if_changed(py_path, build_info_content, updated_files)

    # 6b. Update TypeScript version.ts / src/version.ts / buildInfo.ts
    ts_info_paths = [
        os.path.join(root_dir, "src", "version.ts"),
        os.path.join(root_dir, "version.ts"),
        os.path.join(root_dir, "src", "buildInfo.ts"),
        os.path.join(root_dir, "buildInfo.ts"),
    ]
    target_ts_paths = [p for p in ts_info_paths if os.path.exists(p)]

    is_js_ts_project = (
        os.path.isfile(os.path.join(root_dir, "package.json"))
        or os.path.isfile(os.path.join(root_dir, "tsconfig.json"))
    )

    if not target_ts_paths and is_js_ts_project:
        default_ts_path = (
            os.path.join(root_dir, "src", "version.ts")
            if os.path.isdir(os.path.join(root_dir, "src"))
            else os.path.join(root_dir, "version.ts")
        )
        target_ts_paths = [default_ts_path]

    ts_info_content = f"""// Auto-generated static build metadata updated by stampver.
export const VERSION = "{ctx.semver or ctx.date_str}";
export const COMMIT = "{ctx.commit_hash}";
export const DATE = "{ctx.date_str}";
export const FULL_VERSION = "{ctx.full_version}";
export const BUILD_HASH = "{ctx.build_hash}";
"""
    for ts_path in target_ts_paths:
        _write_if_changed(ts_path, ts_info_content, updated_files)

    # 7. Update HTML meta tags
    html_paths = [os.path.join(root_dir, "index.html")]
    for root, _, files in os.walk(root_dir):
        if "node_modules" in root or ".git" in root or "build" in root or "dist" in root:
            continue
        for file in files:
            if file.endswith(".html"):
                html_paths.append(os.path.join(root, file))

    for h_path in set(html_paths):
        if os.path.isfile(h_path):
            try:
                with open(h_path, encoding="utf-8") as f:
                    h_content = f.read()
                original = h_content
                if '<meta name="version"' in h_content:
                    h_content = re.sub(
                        r'<meta\s+name="version"\s+content="[^"]*"',
                        f'<meta name="version" content="{ctx.full_version}"',
                        h_content,
                    )
                if '<meta name="build-hash"' in h_content:
                    h_content = re.sub(
                        r'<meta\s+name="build-hash"\s+content="[^"]*"',
                        f'<meta name="build-hash" content="{ctx.build_hash}"',
                        h_content,
                    )
                if h_content != original:
                    _write_if_changed(h_path, h_content, updated_files)
            except Exception:
                pass

    # 8. Update Android build.gradle / build.gradle.kts
    gradle_paths = [
        os.path.join(root_dir, "android", "app", "build.gradle.kts"),
        os.path.join(root_dir, "android", "app", "build.gradle"),
    ]
    for g_path in gradle_paths:
        if os.path.isfile(g_path):
            try:
                with open(g_path, encoding="utf-8") as f:
                    g_content = f.read()
                original = g_content
                if ctx.semver:
                    g_content = re.sub(
                        r'versionName\s*=\s*"[^"]+"', f'versionName = "{ctx.semver}"', g_content
                    )
                g_content = re.sub(
                    r"versionCode\s*=\s*\d+", f"versionCode = {ctx.calver_code}", g_content
                )
                if g_content != original:
                    _write_if_changed(g_path, g_content, updated_files)
            except Exception:
                pass

    staged_files: list[str] = []
    if stage and updated_files:
        rel_files = [os.path.relpath(f, root_dir) for f in updated_files]
        try:
            subprocess.run(["git", "add"] + rel_files, cwd=root_dir, check=True)
            staged_files = rel_files
        except Exception:
            pass

    return StampResult(
        context=ctx,
        updated_files=[os.path.relpath(f, root_dir) for f in updated_files],
        staged_files=staged_files,
    )


def _write_if_changed(target_path: str, new_content: str, updated_files: list[str]):
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    if os.path.exists(target_path):
        try:
            with open(target_path, encoding="utf-8") as f:
                if f.read() == new_content:
                    return
        except Exception:
            pass

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    updated_files.append(target_path)
