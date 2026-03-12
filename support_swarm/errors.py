class AgentSpecNotFoundError(KeyError):
    """Raised when a requested agent spec is not present in the registry."""

    def __init__(self, context: str, agent_name: str) -> None:
        super().__init__(f"[{context}] Agent spec '{agent_name}' not found in registry.")
        self.context = context
        self.agent_name = agent_name
