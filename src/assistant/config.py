import os
from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH = Path(os.environ.get("PAI_CONFIG", Path.home() / ".config" / "pai" / "config.yaml"))

_DEFAULTS: dict[str, Any] = {
    "model": "qwen2.5:7b",
    "ollama_host": "http://localhost:11434",
    "microsoft": {},
    "notes": {"folder": "Personal"},
    "search": {"max_results": 5},
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load() -> dict[str, Any]:
    cfg = dict(_DEFAULTS)
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            user = yaml.safe_load(f) or {}
        cfg = _deep_merge(cfg, user)
    return cfg


def config_path() -> Path:
    return _CONFIG_PATH
