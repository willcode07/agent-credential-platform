"""Shared adapter interface for MCP, A2A, and ANP."""

from abc import ABC, abstractmethod


class ProtocolAdapter(ABC):
    """One way for agents to exchange context or tasks.

    Concrete adapters live under ``acp.protocols``. Callers should depend on
    this interface when they only need a description of the channel.

    # OPEN QUESTION: may one user request fan out across adapters (read a
    # credential over MCP, then open an A2A task), or does each adapter stay
    # a separate entry point?
    """

    name: str

    @abstractmethod
    def describe(self) -> dict[str, str]:
        """Return a short, non-normative description of this adapter."""
