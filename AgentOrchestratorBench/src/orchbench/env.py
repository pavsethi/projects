"""Local secrets: load a gitignored ``.env`` and fail fast on missing keys.

A real sweep with no key used to "run" and record every episode as a
``provider_error`` -- a confusing, wasted run. The CLI now loads ``.env`` itself
and refuses to start a real-provider run without a key.

Deliberately dependency-free (no python-dotenv): ``KEY=value`` lines, ``#``
comments, optional ``export`` prefix and surrounding quotes. Variables already
set in the environment always win over the file.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Environment variable each real provider needs.
PROVIDER_KEYS: dict[str, str] = {"anthropic": "ANTHROPIC_API_KEY"}


def load_dotenv(path: Path) -> list[str]:
    """Set variables from ``path`` that aren't already set; return their names.

    Empty values are skipped so a placeholder line (``ANTHROPIC_API_KEY=``)
    never masks a missing key.
    """
    if not path.is_file():
        return []
    loaded = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.removeprefix("export ").partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        if key and value and not os.environ.get(key):
            os.environ[key] = value
            loaded.append(key)
    return loaded


def missing_key(provider: str) -> str | None:
    """Name of the env var ``provider`` needs but lacks, else ``None``."""
    var = PROVIDER_KEYS.get(provider)
    if var and not os.environ.get(var, "").strip():
        return var
    return None
