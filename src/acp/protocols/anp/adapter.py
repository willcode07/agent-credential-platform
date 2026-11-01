"""ANP / DID adapter seam.

ANP-07 (Agent Description Protocol) publishes an agent as a JSON document
with ``protocolType`` ``ANP`` and ``type`` ``AgentDescription``, and
authenticates with the DID methods from ANP-02. A2A publishes an Agent Card
at a well-known HTTP path. This module is where those two descriptions would
be projected onto each other. Nothing is fetched, signed, or validated.

# OPEN QUESTION: when both an ANP Agent Description and an A2A Agent Card
# exist, which one is canonical, and is the other a generated view?
"""

from acp.protocols.a2a.card import AGENT_CARD_WELL_KNOWN_PATH
from acp.protocols.base import ProtocolAdapter


class ANPAdapter(ProtocolAdapter):
    """Long-term identity adapter. Discovery is not implemented."""

    name = "anp"

    def describe(self) -> dict[str, str]:
        return {
            "name": self.name,
            "role": "Decentralized agent identity and discovery via DIDs.",
            "status": "not_implemented",
        }

    def project_did(self, did: str) -> dict[str, str]:
        """Show how a DID would point at an Agent Card. Not a real resolution."""
        if not did.startswith("did:"):
            raise ValueError(f"not a DID: {did}")
        return {
            "did": did,
            "agentCardPath": AGENT_CARD_WELL_KNOWN_PATH,
            "status": "not_implemented",
        }
