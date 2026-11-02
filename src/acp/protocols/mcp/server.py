"""Mock MCP credential store.

Uses the official ``mcp`` Python SDK. Through the 1.x line the high-level
server class was ``FastMCP`` (``mcp.server.fastmcp``). Version 2 renamed it
to ``MCPServer`` and ``pip install mcp`` resolves to 2.x, so this module
imports ``MCPServer``. The decorators (``@tool``, ``@resource``) are the
same idea FastMCP exposed.

# OPEN QUESTION: pin ``mcp>=1.28,<2`` if hosts that embed this server still
# import FastMCP or speak only the 2025 protocol revisions.
# OPEN QUESTION: a model that can call ``read_credential`` sees every claim.
# Production needs a holder-auth check, and counterparties should only be
# offered ``disclose_claims``.
"""

from mcp.server import MCPServer

from acp.credentials.store import CredentialNotFoundError, CredentialStore
from acp.credentials.zkp import SelectiveDisclosureProver
from acp.protocols.base import ProtocolAdapter


class MCPAdapter(ProtocolAdapter):
    """Private-context channel. Credentials do not ride on the A2A task."""

    name = "mcp"

    def describe(self) -> dict[str, str]:
        return {
            "name": self.name,
            "role": "Holder-side context. Tools disclose claims instead of copying the wallet.",
            "sdk": "mcp.server.MCPServer (FastMCP was renamed in mcp 2.x)",
            "status": "in-memory mock store",
        }


def build_server(store: CredentialStore | None = None) -> MCPServer:
    """Create a credential-store MCP server.

    Pass ``store`` in tests. The default data is the education example so
    ``acp mcp`` has credentials to disclose. It is not part of the core model.
    """
    if store is None:
        # Imported lazily so the education example can import this module.
        from acp.verticals.education import education_store

        credential_store = education_store()
    else:
        credential_store = store
    server = MCPServer(
        "acp-credential-store",
        instructions=(
            "Mock private credential store. Prefer disclose_claims. "
            "read_credential returns the full credential and is a stand-in "
            "for the holder's own agent, not for a counterparty."
        ),
    )
    prover = SelectiveDisclosureProver()

    @server.tool()
    def list_credentials(holder_did: str) -> list[dict[str, str]]:
        """List credential ids and types for a holder. Claim values are omitted."""
        return credential_store.summaries_for_holder(holder_did)

    @server.tool()
    def disclose_claims(credential_id: str, reveal: list[str]) -> dict[str, object]:
        """Return a mock selective-disclosure proof for the named claims only."""
        try:
            credential = credential_store.get(credential_id)
        except CredentialNotFoundError as exc:
            raise ValueError(f"unknown credential: {credential_id}") from exc
        proof = prover.prove(credential, reveal)
        return proof.model_dump()

    @server.resource("credential://{credential_id}")
    def read_credential(credential_id: str) -> str:
        """Read one stored credential, including claims the matcher should not see."""
        try:
            credential = credential_store.get(credential_id)
        except CredentialNotFoundError as exc:
            raise ValueError(f"unknown credential: {credential_id}") from exc
        return credential.model_dump_json(by_alias=True)

    return server
