from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_REQUIRED_KEYS: frozenset[str] = frozenset({"name", "user_prompt"})


def load_yaml(path: Path) -> dict | None:
    """Read a YAML file from disk and return validated data.

    Args:
        path: Absolute path to the ``.yaml`` file.

    Returns:
        Validated dict on success, ``None`` if the file is missing or invalid.
    """
    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return validate_yaml(data)
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("Failed to load %s: %s", path, exc)
        return None


def parse_yaml(content: str) -> dict | None:
    """Parse a raw YAML string.

    Args:
        content: Raw YAML text.

    Returns:
        Parsed dict on success, ``None`` on parse error.
    """
    try:
        return yaml.safe_load(content)
    except yaml.YAMLError as exc:
        logger.warning("YAML parse error: %s", exc)
        return None


def validate_yaml(data: object) -> dict | None:
    """Assert the parsed object is a mapping that contains required agent keys.

    Args:
        data: Object produced by ``yaml.safe_load``.

    Returns:
        The original dict if valid, ``None`` otherwise.
    """
    if not isinstance(data, dict):
        logger.warning("Expected a YAML mapping, got %s", type(data).__name__)
        return None

    missing = _REQUIRED_KEYS - data.keys()
    if missing:
        logger.warning("Agent spec missing required keys: %s", sorted(missing))
        return None

    return data
