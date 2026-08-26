"""
stampver: Universal date-first versioning and build stamping CLI tool.
"""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("stampver")
except Exception:
    __version__ = "0.2.0"
