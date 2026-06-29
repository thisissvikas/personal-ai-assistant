import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

_ENV_PATH = Path(os.environ.get("PAI_ENV_FILE", Path.home() / ".config" / "pai" / ".env"))


def load() -> dict[str, Any]:
    file_vals = dotenv_values(_ENV_PATH)

    def _get(key: str, default: str) -> str:
        return os.environ.get(key) or file_vals.get(key) or default

    return {
        "model": _get("PAI_MODEL", "qwen2.5:7b"),
        "ollama_host": _get("PAI_OLLAMA_HOST", "http://localhost:11434"),
        "microsoft": {
            "client_id": _get("MICROSOFT_CLIENT_ID", ""),
            "tenant_id": _get("MICROSOFT_TENANT_ID", ""),
        },
        "notes": {
            "folder": _get("PAI_NOTES_FOLDER", "Personal"),
        },
        "search": {
            "max_results": int(_get("PAI_SEARCH_MAX_RESULTS", "5")),
        },
    }


def config_path() -> Path:
    return _ENV_PATH
