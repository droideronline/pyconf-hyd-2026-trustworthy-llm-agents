"""Agent spec registry — declarative YAML loader.

Scans the ``declarative/specs/`` directory for agent YAML files and builds
a flat  name → AgentSpec  mapping.  The registry is populated eagerly at
import time so every other module can simply do::

    from customer_support_agent.declarative import AGENT_SPECS, get_agent_spec
"""

import logging
from pathlib import Path

from support_swarm.declarative.models import AgentSpec, SpecRegistry
from support_swarm.declarative.yaml_utils import load_yaml
from support_swarm.enums import Agents
from support_swarm.errors import AgentSpecNotFoundError

logger = logging.getLogger(__name__)

# Path to agent YAML specs — lives next to this file
AGENT_SPECS_DIR = Path(__file__).parent / "agents"

# YAML stems that are not agent definitions
_SKIP_STEMS: frozenset[str] = frozenset({"schema", "__init__"})

# Module-level registry (populated at the bottom of this file)
AGENT_SPECS: SpecRegistry


def load_agent_specs() -> SpecRegistry:
    """Scan *AGENT_SPECS_DIR* and return a populated registry.

    All ``.yaml`` files (except those in ``_SKIP_STEMS``) are treated as agent
    specs.  Files that fail validation are skipped with a warning.

    Returns:
        Flat ``name → AgentSpec`` mapping.
    """
    registry: SpecRegistry = {}

    spec_stems = {
        f.stem
        for f in AGENT_SPECS_DIR.iterdir()
        if f.is_file() and f.suffix == ".yaml" and f.stem not in _SKIP_STEMS
    }

    for stem in sorted(spec_stems):
        spec_data = load_yaml(AGENT_SPECS_DIR / f"{stem}.yaml")
        if spec_data:
            registry[spec_data["name"]] = AgentSpec.model_validate(spec_data)

    logger.info("Loaded %d agent spec(s): %s", len(registry), sorted(registry))
    return registry


def get_agent_spec(agent_name: Agents) -> AgentSpec:
    """Look up an agent specification by enum value.

    Args:
        agent_name: Member of the :class:`~customer_support_agent.enums.Agents` enum.

    Returns:
        The matching :class:`~customer_support_agent.declarative.models.AgentSpec`.

    Raises:
        AgentSpecNotFoundError: When the agent name is absent from the registry.
    """
    try:
        return AGENT_SPECS[agent_name.value]
    except KeyError as exc:
        raise AgentSpecNotFoundError("support_swarm", agent_name.value) from exc


# ── Eagerly populate the registry on import ──────────────────────────────────
AGENT_SPECS: SpecRegistry = load_agent_specs()
