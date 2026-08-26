"""Stylised file writers - one class per generated artifact.

Each writer knows its template and renders it from a ``VersionContext``.
The engine routes target discovery and let ``write_if_changed`` handle I/O.
"""

import json
import re

from stampver.core import VersionContext


class Writer:
    path: str

    def __init__(self, path: str):
        self.path = path

    def render(self, ctx: VersionContext) -> str:
        raise NotImplementedError


class VersionTxtWriter(Writer):
    """version.txt - semantic base for SemVer repos, stamp date for date repos."""

    def render(self, ctx: VersionContext) -> str:
        return (ctx.semver if ctx.semver else ctx.date_str) + "\n"


class BuildInfoPyWriter(Writer):
    """build_info.py - generic build metadata consumer template."""

    _TEMPLATE = '''"""Auto-generated static build metadata.
Updated by stampver. Do not edit manually.
"""

VERSION = "{version}"
COMMIT = "{commit_hash}"
DATE = "{date_str}"
FULL_VERSION = "{full_version}"
BUILD_HASH = "{build_hash}"
'''

    def render(self, ctx: VersionContext) -> str:
        return self._TEMPLATE.format(
            version=ctx.version,
            commit_hash=ctx.commit_hash,
            date_str=ctx.date_str,
            full_version=ctx.full_version,
            build_hash=ctx.build_hash,
        )


class VersionPyWriter(Writer):
    """version.py - legacy consumer template (VERSION/COMMIT_HASH/BUILD_DATE/FULL_VERSION)."""

    _TEMPLATE = '''"""Auto-generated version file. Do not edit manually."""

VERSION = "{version}"
COMMIT_HASH = "{commit_hash}"
BUILD_DATE = "{build_date}"
FULL_VERSION = "{version} ({commit_hash})"

__all__ = ["VERSION", "COMMIT_HASH", "BUILD_DATE", "FULL_VERSION"]
'''

    def render(self, ctx: VersionContext) -> str:
        return self._TEMPLATE.format(
            version=ctx.version,
            commit_hash=ctx.commit_hash,
            build_date=ctx.build_date,
        )


class VersionTsWriter(Writer):
    """version.ts / buildInfo.ts - TypeScript export template."""

    _TEMPLATE = """// Auto-generated static build metadata updated by stampver.
export const VERSION = "{version}";
export const COMMIT = "{commit_hash}";
export const DATE = "{date_str}";
export const FULL_VERSION = "{full_version}";
export const BUILD_HASH = "{build_hash}";
"""

    def render(self, ctx: VersionContext) -> str:
        return self._TEMPLATE.format(
            version=ctx.version,
            commit_hash=ctx.commit_hash,
            date_str=ctx.date_str,
            full_version=ctx.full_version,
            build_hash=ctx.build_hash,
        )


class VersionJsWriter(Writer):
    """version.js - browser consumer template (window globals)."""

    _TEMPLATE = """// Auto-generated version file. Do not edit manually.
window.APP_VERSION = "{version}";
window.COMMIT_HASH = "{commit_hash}";
window.BUILD_DATE = "{build_date}";
window.FULL_VERSION = "{version} ({commit_hash})";
"""

    def render(self, ctx: VersionContext) -> str:
        return self._TEMPLATE.format(
            version=ctx.version,
            commit_hash=ctx.commit_hash,
            build_date=ctx.build_date,
        )


class PackageJsonWriter(Writer):
    """package.json version + build metadata keys."""

    def render(self, ctx: VersionContext) -> str:
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        if ctx.semver:
            data["version"] = ctx.semver
        data["buildDate"] = ctx.date_str
        data["buildHash"] = ctx.build_hash
        return json.dumps(data, indent=2) + "\n"


class ManifestJsonWriter(Writer):
    """chrome_extension/manifest.json version + version_name."""

    def render(self, ctx: VersionContext) -> str:
        with open(self.path, encoding="utf-8") as f:
            manifest = json.load(f)
        if ctx.semver:
            manifest["version"] = ctx.semver
        manifest["version_name"] = ctx.full_version
        return json.dumps(manifest, indent=2) + "\n"


class PyprojectWriter(Writer):
    """pyproject.toml [project] version line."""

    def render(self, ctx: VersionContext) -> str:
        content = read_file(self.path)
        project_match = re.search(r"\[project\][\s\S]*?(?=\n\[|\Z)", content)
        if not project_match:
            return content
        orig_block = project_match.group(0)
        new_block = re.sub(
            r'^(version\s*=\s*)"[^"]+"',
            f'\\1"{ctx.version}"',
            orig_block,
            flags=re.MULTILINE,
        )
        return content[: project_match.start()] + new_block + content[project_match.end() :]


class CargoWriter(Writer):
    """Cargo.toml [package] version line (SemVer repos only)."""

    def render(self, ctx: VersionContext) -> str:
        content = read_file(self.path)
        return re.sub(
            r'(\[package\][\s\S]*?\bversion\s*=\s*)"[^"]+"',
            f'\\1"{ctx.semver}"',
            content,
            count=1,
        )


class InitPyWriter(Writer):
    """__init__.py __version__ assignment (SemVer repos only)."""

    def render(self, ctx: VersionContext) -> str:
        content = read_file(self.path)
        return re.sub(
            r'(__version__\s*=\s*)"[^"]+"',
            f'\\1"{ctx.semver}"',
            content,
        )


class GradleWriter(Writer):
    """Android build.gradle(.kts) versionName/versionCode."""

    def render(self, ctx: VersionContext) -> str:
        content = read_file(self.path)
        if ctx.semver:
            content = re.sub(r'versionName\s*=\s*"[^"]+"', f'versionName = "{ctx.semver}"', content)
        return re.sub(r"versionCode\s*=\s*\d+", f"versionCode = {ctx.calver_code}", content)


class HtmlWriter(Writer):
    """HTML: <meta name="version"> + <meta name="build-hash"> and/or ?v= cache busting."""

    def __init__(
        self,
        path: str,
        meta: bool = True,
        cache_bust: bool = False,
        cache_bust_regex: str = r"(\.(?:css|js)\?v=)[^\"'\s>]+",
    ):
        super().__init__(path)
        self.meta = meta
        self.cache_bust = cache_bust
        self.cache_bust_regex = cache_bust_regex

    def render(self, ctx: VersionContext) -> str:
        content = read_file(self.path)
        original = content
        if self.meta and '<meta name="version"' in content:
            content = re.sub(
                r'<meta\s+name="version"\s+content="[^"]*"',
                f'<meta name="version" content="{ctx.full_version}"',
                content,
            )
        if self.meta and '<meta name="build-hash"' in content:
            content = re.sub(
                r'<meta\s+name="build-hash"\s+content="[^"]*"',
                f'<meta name="build-hash" content="{ctx.build_hash}"',
                content,
            )
        if self.cache_bust:
            content = re.sub(
                self.cache_bust_regex,
                lambda m: m.group(1) + ctx.version,
                content,
            )
        return content if content != original else original


def read_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()
