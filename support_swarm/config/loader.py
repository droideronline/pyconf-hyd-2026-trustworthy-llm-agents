from __future__ import annotations

import os
import re
from pathlib import Path
from string import Template
from typing import Any

import yaml
from dotenv import load_dotenv

from support_swarm.config.settings import Settings

_UNRESOLVED_RE = re.compile(r"^\$[A-Z_][A-Z0-9_]*$")

_SETTINGS_PATH = Path(__file__).resolve().parents[2] / "settings.yaml"
_ROOT_DIR = _SETTINGS_PATH.parent

_config: Settings | None = None


def _strip_unresolved(obj: Any) -> Any:
    """Remove values that are still unresolved $VAR placeholders."""
    if isinstance(obj, dict):
        return {
            k: v
            for k, v in ((k, _strip_unresolved(v)) for k, v in obj.items())
            if v is not None
        }
    if isinstance(obj, list):
        return [_strip_unresolved(v) for v in obj]
    if isinstance(obj, str) and _UNRESOLVED_RE.match(obj):
        return None
    return obj


def _read_dotenv() -> None:
    """Load .env from the project root if it exists."""
    env_file = _ROOT_DIR / ".env"
    if env_file.is_file():
        load_dotenv(env_file, override=False)


def _parse_config_file(path: Path) -> dict[str, Any]:
    """Read YAML and substitute $VAR / ${VAR} from environment."""
    text = path.read_text(encoding="utf-8")
    text = Template(text).safe_substitute(os.environ)
    data = yaml.safe_load(text)
    return _strip_unresolved(data)


def load_settings(path: Path | None = None) -> Settings:
    """Load .env, resolve env vars in YAML, and validate settings."""
    global _config
    _read_dotenv()
    data = _parse_config_file(path or _SETTINGS_PATH)
    _config = Settings.model_validate(data)
    return _config


def get_settings() -> Settings:
    """Return the loaded settings singleton."""
    if _config is None:
        return load_settings()
    return _config
