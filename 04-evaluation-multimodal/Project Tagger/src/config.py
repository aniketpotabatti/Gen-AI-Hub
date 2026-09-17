"""Configuration loading for models.yaml and tags_schema.yaml.

Resolves `${ENV_VAR}` placeholders against the process environment (plus an
optional `.env` file via python-dotenv).
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"

_ENV_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _resolve_env_placeholders(value: Any) -> Any:
    """Recursively replace `${VAR}` strings with `os.environ` values."""
    if isinstance(value, str):
        def _replace(match: re.Match) -> str:
            return os.environ.get(match.group(1), match.group(0))

        return _ENV_PLACEHOLDER.sub(_replace, value)
    if isinstance(value, dict):
        return {key: _resolve_env_placeholders(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_env_placeholders(item) for item in value]
    return value


def _load_yaml(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_models_config(config_dir: Path = CONFIG_DIR) -> dict:
    """Load and env-resolve `config/models.yaml`."""
    raw = _load_yaml(Path(config_dir) / "models.yaml")
    return _resolve_env_placeholders(raw)


def load_tags_schema(config_dir: Path = CONFIG_DIR) -> dict:
    """Load `config/tags_schema.yaml` (tag taxonomy / allowed values)."""
    return _load_yaml(Path(config_dir) / "tags_schema.yaml")
