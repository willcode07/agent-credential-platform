"""ANP view derived from the A2A Agent Card.

Decided 2026-11-02: there is one matching agent, and the Agent Card is the
source of truth. This module emits an unsigned ANP Agent Description stub
from that card. It does not resolve a DID and it does not sign the document.

# OPEN QUESTION: did:web and did:wba document proofs are not verified here.
# See ``acp.credentials.did``.
"""

from acp.protocols.a2a.card import build_agent_card
from acp.protocols.base import ProtocolAdapter


class ANPAdapter(ProtocolAdapter):
    """Derived ANP description. The Agent Card wins if the two disagree."""

    name = "anp"

    def describe(self) -> dict[str, str]:
        return {
            "name": self.name,
            "role": "Unsigned ANP Agent Description derived from the A2A Agent Card.",
            "sourceOfTruth": "a2a-agent-card",
            "status": "derived_stub",
        }

    def project_card(self, card: dict[str, object] | None = None) -> dict[str, object]:
        """Build an ANP Agent Description stub from the Agent Card."""
        source = card if card is not None else build_agent_card("http://127.0.0.1:8000")
        interfaces = source.get("supportedInterfaces")
        url = ""
        if isinstance(interfaces, list) and interfaces and isinstance(interfaces[0], dict):
            raw_url = interfaces[0].get("url")
            url = raw_url if isinstance(raw_url, str) else ""
        return {
            "protocolType": "ANP",
            "protocolVersion": "1.0.0",
            "type": "AgentDescription",
            "name": source.get("name", ""),
            "description": source.get("description", ""),
            "url": url,
            "status": "derived_stub",
            "sourceOfTruth": "a2a-agent-card",
        }

    def project_did(self, did: str) -> dict[str, str]:
        """Point a DID at the card. The DID is not resolved; the card is canonical."""
        if not did.startswith("did:"):
            raise ValueError(f"not a DID: {did}")
        return {
            "did": did,
            "status": "derived_stub",
            "sourceOfTruth": "a2a-agent-card",
            "note": "ANP documents are generated from the Agent Card. This DID is not resolved.",
        }
