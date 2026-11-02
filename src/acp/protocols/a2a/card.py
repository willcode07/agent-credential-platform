"""A2A Agent Card for the matching agent.

Verified against A2A protocol 1.0.0 (https://a2a-protocol.org/latest/specification/):
the well-known URI is ``/.well-known/agent-card.json``. The 0.3.0 release
renamed it from ``/.well-known/agent.json``.

The JSON-RPC URL is not a well-known path. Spec section 9.2 illustrates
``POST /rpc``. The sample cards use an agent-chosen URL such as
``https://example.com/a2a/v1``. This app serves the URL it publishes on the
card (``/a2a/v1``) and the illustrative ``/rpc`` alias.

# OPEN QUESTION: what public origin should ``supportedInterfaces[].url``
# use once this sits behind TLS and a proxy? The spec asks for an absolute
# HTTPS URL in production.
"""

AGENT_CARD_WELL_KNOWN_PATH = "/.well-known/agent-card.json"
# Retired in A2A 0.3.0. Served nowhere, so clients on the old path fail loudly.
RETIRED_AGENT_CARD_PATH = "/.well-known/agent.json"
JSONRPC_PATH = "/a2a/v1"
JSONRPC_ALIAS_PATH = "/rpc"

# Sample cards in the 1.0.0 spec use "1.0". Some request examples still send
# the header `A2A-Version: 0.3`. We advertise the released spec version.
PROTOCOL_VERSION = "1.0"


def build_agent_card(base_url: str) -> dict[str, object]:
    """Return an Agent Card whose preferred interface points at this process."""
    root = base_url.rstrip("/")
    return {
        "name": "ACP Matching Agent",
        "description": (
            "Matches candidates to opportunities from selectively disclosed "
            "credentials. Private claim stores stay on MCP; this card is the A2A "
            "collaboration surface. Markets such as education or hiring supply "
            "their own claim requirements."
        ),
        "supportedInterfaces": [
            {
                "url": f"{root}{JSONRPC_PATH}",
                "protocolBinding": "JSONRPC",
                "protocolVersion": PROTOCOL_VERSION,
            }
        ],
        "provider": {
            "organization": "Agent Credential Platform",
            "url": "https://github.com/willcode07/agent-credential-platform",
        },
        "version": "0.1.0",
        "documentationUrl": "https://github.com/willcode07/agent-credential-platform/blob/main/docs/protocols.md",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "extendedAgentCard": False,
        },
        "defaultInputModes": ["text/plain", "application/json"],
        "defaultOutputModes": ["text/plain", "application/json"],
        "skills": [
            {
                "id": "match-candidates",
                "name": "Match candidates to an opportunity",
                "description": (
                    "Rank holders against an opportunity's claim requirements. "
                    "Only revealed claims are visible to the matcher."
                ),
                "tags": ["matching", "credentials"],
                "examples": [
                    "Which disclosed candidates satisfy this opportunity's requirements?"
                ],
            },
            {
                "id": "verify-disclosure",
                "name": "Check a selective disclosure",
                "description": (
                    "Check that a disclosure names a trusted issuer. "
                    "This build's check is a mock, not a cryptographic proof."
                ),
                "tags": ["credentials", "disclosure"],
                "examples": [
                    "Which claims does this disclosure reveal, and is the issuer trusted?"
                ],
            },
        ],
    }
