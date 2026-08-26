"""Repository configuration for stampver.

Priority order: CLI flags > environment > ``stampver.toml`` > built-in defaults.
"""

import os
import tomllib
from dataclasses import dataclass, field
from typing import Any

CONFIG_FILE = "stampver.toml"
SUPPORTED_FORMATS = ("auto", "semver", "semverrun", "date")


@dataclass
class StampverConfig:
    format: str = "auto"
    salt: str = ""
    version_txt: str | None = "version.txt"
    pyproject: bool | None = None
    gradle: bool | None = None
    build_info: list[str] = field(default_factory=list)
    version_py: list[str] = field(default_factory=list)
    version_js: list[str] = field(default_factory=list)
    version_ts: list[str] = field(default_factory=list)
    html_meta: list[str] = field(default_factory=list)
    html_cache_bust: list[str] = field(default_factory=list)
    cache_bust_regex: str = r"(\.(?:css|js)\?v=)[^\"'\s>]+"

    @classmethod
    def load(cls, root_dir: str) -> "StampverConfig":
        config_path = os.path.join(root_dir, CONFIG_FILE)
        if not os.path.isfile(config_path):
            return cls()
        with open(config_path, "rb") as f:
            return cls.from_mapping(tomllib.load(f))

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "StampverConfig":
        cfg = cls()
        if not data:
            return cfg

        fmt = str(data.get("format", cfg.format))
        if fmt not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Invalid stampver.toml format {fmt!r}; expected one of {SUPPORTED_FORMATS}"
            )
        cfg.format = fmt
        cfg.salt = str(data.get("salt", cfg.salt))
        if "version_txt" in data:
            cfg.version_txt = data["version_txt"]
        if "pyproject" in data:
            cfg.pyproject = bool(data["pyproject"])
        if "gradle" in data:
            cfg.gradle = bool(data["gradle"])
        for key in (
            "build_info",
            "version_py",
            "version_js",
            "version_ts",
            "html_meta",
            "html_cache_bust",
        ):
            value = data.get(key)
            if value:
                setattr(cfg, key, [str(p) for p in value])
        if data.get("cache_bust_regex"):
            cfg.cache_bust_regex = str(data["cache_bust_regex"])
        return cfg

    def format_for(self, has_semver: bool) -> str:
        if self.format == "auto":
            return "semver" if has_semver else "date"
        return self.format
