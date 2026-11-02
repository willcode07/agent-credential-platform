"""Mock MCP credential store.

Uses the official ``mcp`` Python SDK. Through the 1.x line the high-level
server class was ``FastMCP`` (``mcp.server.fastmcp``). Version 2 renamed it
to ``MCPServer`` and ``pip install mcp`` resolves to 2.x, so this module
imports ``MCPServer``. The decorators (``@tool``, ``@resource``) are the
same idea FastMCP exposed.

# OPEN QUESTION: pin ``mcp>=1.28,<2`` if hosts that embed this server still
# import FastMCP or speak only the 2025 protocol revisions.
"""

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from acp.credentials.auth import HolderAuthError, require_holder
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
            "Private credential store. Counterparties use disclose_claims. "
            "read_credential returns the full credential only when holder_proof "
            "authenticates the holder. A missing proof is denied."
        ),
    )
    prover = SelectiveDisclosureProver()

    @server.tool()
    def list_credentials(holder_did: str) -> list[dict[str, str]]:
        """List credential ids and types for a holder. Claim values are omitted."""
        return credential_store.summaries_for_holder(holder_did)

    @server.tool()
    def disclose_claims(credential_id: str, reveal: list[str]) -> dict[str, object]:
        """Open an SD-JWT for the named claims. Hidden claims stay out of the result."""
        try:
            credential = credential_store.get(credential_id)
        except CredentialNotFoundError as exc:
            raise ToolError(f"unknown credential: {credential_id}") from exc
        proof = prover.prove(credential, reveal)
        credential_store.record_disclosure(credential_id)
        return proof.model_dump()

    @server.tool()
    def read_credential(credential_id: str, holder_proof: str = "") -> str:
        """Return the full credential. Denied unless holder_proof matches the holder."""
        try:
            credential = credential_store.get(credential_id)
        except CredentialNotFoundError as exc:
            raise ToolError(f"unknown credential: {credential_id}") from exc
        holder = credential.holder_did() or ""
        try:
            require_holder(holder, holder_proof)
        except HolderAuthError as exc:
            raise ToolError(str(exc)) from exc
        return credential.model_dump_json(by_alias=True)

    return server
