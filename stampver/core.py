"""Core version math: contexts, resolution, and hashing.

Pure data and helpers only - no file I/O (see ``engine.py`` and ``writers.py``).
"""

import datetime
import hashlib
import hmac
import json
import logging
import os
import re
import subprocess
from collections.abc import Mapping


class VersionContext:
    """Resolved version data for one stamp run."""

    def __init__(
        self,
        version: str,
        semver: str | None,
        date_str: str,
        build_date: str,
        run_number: str | None,
        calver_code: str,
        commit_hash: str,
        full_version: str,
        build_hash: str,
        format: str,
    ):
        self._version = version
        self._semver = semver
        self._date_str = date_str
        self._build_date = build_date
        self._run_number = run_number
        self._calver_code = calver_code
        self._commit_hash = commit_hash
        self._full_version = full_version
        self._build_hash = build_hash
        self._format = format

    @property
    def version(self) -> str:
        return self._version

    @property
    def semver(self) -> str | None:
        return self._semver

    @property
    def date_str(self) -> str:
        return self._date_str

    @property
    def build_date(self) -> str:
        return self._build_date

    @property
    def run_number(self) -> str | None:
        return self._run_number

    @property
    def calver_code(self) -> str:
        return self._calver_code

    @property
    def commit_hash(self) -> str:
        return self._commit_hash

    @property
    def full_version(self) -> str:
        return self._full_version

    @property
    def build_hash(self) -> str:
        return self._build_hash

    @property
    def format(self) -> str:
        return self._format


DATE_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}(-\d{2}\d{2})?$")
SEMVER_RE = re.compile(r"^v?\d+\.\d+(\.\d+)?$")


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
    except Exception as e:
        logging.debug("Failed to get git commit hash: %s", e)
        return "unknown"


def generate_build_hash(version_str: str, date_str: str, commit_hash: str, salt: str = "") -> str:
    raw_payload = f"{version_str}:{date_str}:{commit_hash}".encode()
    key = salt.encode() if salt else b"stampver"
    return hmac.new(key, raw_payload, hashlib.sha256).hexdigest()


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


def looks_like_date(value: str) -> bool:
    return DATE_RE.match(value) is not None


def detect_semver(root_dir: str) -> str | None:
    """Auto-detect a SemVer base from version.txt / package.json / Cargo.toml / pyproject.toml.

    A date-style string (``YYYY.MM.DD-HHMM``) is never reported as SemVer.
    """
    version_txt = os.path.join(root_dir, "version.txt")
    if os.path.isfile(version_txt):
        try:
            with open(version_txt, encoding="utf-8") as f:
                line = f.readline().strip()
                if line and not looks_like_date(line):
                    m = SEMVER_RE.match(line)
                    if m:
                        return m.group(0).lstrip("v")
        except Exception as e:
            logging.debug("Error reading version.txt: %s", e)

    pkg_json = os.path.join(root_dir, "package.json")
    if os.path.isfile(pkg_json):
        try:
            with open(pkg_json, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data.get("version"), str) and not looks_like_date(data["version"]):
                    return data["version"].lstrip("v")
        except Exception as e:
            logging.debug("Error reading package.json: %s", e)

    cargo_toml = os.path.join(root_dir, "Cargo.toml")
    if os.path.isfile(cargo_toml):
        try:
            with open(cargo_toml, encoding="utf-8") as f:
                content = f.read()
                m = re.search(r'\[package\][\s\S]*?\bversion\s*=\s*"([^"]+)"', content)
                if m and not looks_like_date(m.group(1)):
                    return m.group(1).lstrip("v")
        except Exception as e:
            logging.debug("Error reading Cargo.toml: %s", e)

    pyproject_toml = os.path.join(root_dir, "pyproject.toml")
    if os.path.isfile(pyproject_toml):
        try:
            content = read_file(pyproject_toml)
            project_match = re.search(r"\[project\][\s\S]*?(?=\n\[|\Z)", content)
            if project_match:
                m = re.search(
                    r'^\s*version\s*=\s*"([^"]+)"', project_match.group(0), flags=re.MULTILINE
                )
                if m and not looks_like_date(m.group(1)):
                    return m.group(1).lstrip("v")
        except Exception as e:
            logging.debug("Error reading pyproject.toml: %s", e)

    return None


def fmt_build_date(date_str: str) -> str:
    """Convert ``YYYY.MM.DD-HHMM`` to ``YYYY-MM-DD HH:MM``."""
    if not date_str or "-" not in date_str:
        return date_str.replace(".", "-")
    date_part, time_part = date_str.split("-", 1)
    date_part = date_part.replace(".", "-")
    return f"{date_part} {time_part[:2]}:{time_part[2:]}"


def fmt_calver_code(date_str: str) -> str:
    """YYYYMMDDHH int-32-friendly code from ``YYYY.MM.DD-HHMM``."""
    if "-" not in date_str:
        raise ValueError(f"Invalid date string: {date_str!r}")
    date_part, time_part = date_str.split("-", 1)
    return date_part.replace(".", "") + time_part[:2]


def build_full_version(
    format_key: str, semver: str | None, date_str: str, run_number: str | None
) -> str:
    if semver:
        full = f"v{semver}-{date_str}"
        if format_key == "semverrun" and run_number:
            full = f"{full}-{run_number}"
        return full
    return date_str


def resolve_context(
    root_dir: str,
    format_key: str = "auto",
    bump: str | None = None,
    salt: str = "",
    env: Mapping[str, str] | None = None,
) -> VersionContext:
    """Resolve the full version context for a project root.

    Environment overrides (CI-friendly):
      * ``BUILD_FULL_VERSION`` - exact full version string
      * ``BUILD_TIMESTAMP``    - YYYY.MM.DD-HHMM (UTC assumed)
      * ``BUILD_VERSION_BASE`` - forces semver base (or date base in date mode)
      * ``BUILD_RUN_NUMBER``   - CI run number appended in semverrun mode
    """
    env = env if env is not None else os.environ

    date_str = env.get("BUILD_TIMESTAMP") or datetime.datetime.now(datetime.UTC).strftime(
        "%Y.%m.%d-%H%M"
    )
    build_date = fmt_build_date(date_str)
    calver_code = fmt_calver_code(date_str)
    commit_hash = get_git_commit(root_dir)

    semver = detect_semver(root_dir)
    env_base = env.get("BUILD_VERSION_BASE")
    if env_base:
        semver = env_base.lstrip("v")
    if bump:
        semver = bump_semver(semver or "0.1.0", bump)

    if format_key == "auto":
        format_key = "semver" if semver else "date"
    if format_key == "date":
        semver = None

    version = semver if semver else date_str
    run_number = env.get("BUILD_RUN_NUMBER")
    full_version = env.get("BUILD_FULL_VERSION") or build_full_version(
        format_key, semver, date_str, run_number
    )
    build_hash = generate_build_hash(version, date_str, commit_hash, salt)

    return VersionContext(
        version=version,
        semver=semver,
        date_str=date_str,
        build_date=build_date,
        run_number=run_number,
        calver_code=calver_code,
        commit_hash=commit_hash,
        full_version=full_version,
        build_hash=build_hash,
        format=format_key,
    )


def read_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()
