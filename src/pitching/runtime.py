"""Portable headless plotting cache defaults for read-only cloud home folders."""

import os
import tempfile
from pathlib import Path


def configure_plot_cache() -> None:
    # Respect explicit user settings. Caches contain no research observations.
    uid = str(os.getuid()) if hasattr(os, "getuid") else "user"
    cache = Path(tempfile.gettempdir()) / f"pitching-cache-{uid}"
    os.environ.setdefault("XDG_CACHE_HOME", str(cache))
    os.environ.setdefault("MPLCONFIGDIR", str(cache / "matplotlib"))
