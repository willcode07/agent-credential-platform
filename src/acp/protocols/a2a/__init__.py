"""A2A adapter: Agent Card plus the JSON-RPC task handler."""

from acp.protocols.a2a.card import (
    AGENT_CARD_WELL_KNOWN_PATH,
    JSONRPC_ALIAS_PATH,
    JSONRPC_PATH,
    build_agent_card,
)
from acp.protocols.a2a.tasks import TaskService, handle_jsonrpc
from acp.protocols.base import ProtocolAdapter

__all__ = [
    "AGENT_CARD_WELL_KNOWN_PATH",
    "A2AAdapter",
    "JSONRPC_ALIAS_PATH",
    "JSONRPC_PATH",
    "TaskService",
    "build_agent_card",
    "handle_jsonrpc",
]


class A2AAdapter(ProtocolAdapter):
    """Collaboration channel. Discovery is the Agent Card; work is a Task."""

    name = "a2a"

    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        self.base_url = base_url

    def describe(self) -> dict[str, str]:
        return {
            "name": self.name,
            "role": "Agent discovery and task collaboration between organizations.",
            "agentCard": AGENT_CARD_WELL_KNOWN_PATH,
            "jsonrpc": JSONRPC_PATH,
            "jsonrpcAlias": JSONRPC_ALIAS_PATH,
            "status": "placeholder task handler; no streaming or push",
        }

    def agent_card(self) -> dict[str, object]:
        return build_agent_card(self.base_url)
