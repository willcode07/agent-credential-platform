"""Smoke test for the MCP credential store.

Uses the SDK's in-memory client so the test does not open a port. The server
class is ``MCPServer``. ``FastMCP`` was the name of this class in mcp 1.x.
"""

import asyncio
import json

from mcp import Client

from acp.protocols.mcp.server import build_server
from acp.verticals.education import ADA_HOME_ADDRESS, TEACHER_ADA


def test_list_and_disclose_do_not_return_hidden_claims() -> None:
    server = build_server()

    async def _run() -> tuple[object, object]:
        async with Client(server) as client:
            listed = await client.call_tool("list_credentials", {"holder_did": TEACHER_ADA})
            disclosed = await client.call_tool(
                "disclose_claims",
                {"credential_id": "vc-license-ada", "reveal": ["license_status"]},
            )
            return listed, disclosed

    listed, disclosed = asyncio.run(_run())
    listed_text = _result_text(listed)
    disclosed_text = _result_text(disclosed)
    assert "vc-license-ada" in listed_text
    assert ADA_HOME_ADDRESS not in listed_text
    assert "active" in disclosed_text
    assert ADA_HOME_ADDRESS not in disclosed_text


def _result_text(result: object) -> str:
    """Flatten whatever the SDK returned into text for a smoke assertion."""
    if hasattr(result, "model_dump"):
        return json.dumps(result.model_dump())
    return json.dumps(result, default=str)
