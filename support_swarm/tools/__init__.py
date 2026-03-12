# Import every tool module so @register_tool decorators execute
import support_swarm.tools.shared as _shared  # noqa: F401
import support_swarm.tools.shop_assist_tools as _shop_assist_tools  # noqa: F401

from support_swarm.tools.registry import get_tools, registry  # noqa: F401
