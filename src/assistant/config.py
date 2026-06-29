import functools
import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

_ENV_PATH = Path(os.environ.get("PAI_ENV_FILE", ".env"))


@functools.lru_cache(maxsize=1)
def load() -> dict[str, Any]:
    """Load configuration from the .env file and environment variables.

    Resolution order (highest priority first):
    1. Shell environment variables (e.g. ``export PAI_MODEL=llama3.1:latest``)
    2. Values in the .env file at ``_ENV_PATH``
    3. Built-in defaults

    Uses ``dotenv_values()`` rather than ``load_dotenv()`` to avoid mutating
    ``os.environ``, which keeps tests isolated from each other.
    """
    file_values = dotenv_values(_ENV_PATH)

    def _resolve(key: str, default: str) -> str:
        if (val := os.environ.get(key)) is not None:
            return val
        if (val := file_values.get(key)) is not None:
            return val
        return default

    return {
        "model": _resolve("PAI_MODEL", "qwen2.5:7b"),
        "ollama_host": _resolve("PAI_OLLAMA_HOST", "http://localhost:11434"),
        "timezone": _resolve("PAI_TIMEZONE", ""),
        "microsoft": {
            "client_id": _resolve("MICROSOFT_CLIENT_ID", ""),
            "tenant_id": _resolve("MICROSOFT_TENANT_ID", ""),
        },
        "notes": {
            "folder": _resolve("PAI_NOTES_FOLDER", "Personal"),
        },
        "search": {
            "max_results": int(_resolve("PAI_SEARCH_MAX_RESULTS", "5")),
        },
    }


def config_path() -> Path:
    """Return the path to the active .env file."""
    return _ENV_PATH
