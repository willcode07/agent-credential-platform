"""Smoke test for the MCP credential store.

Uses the SDK's in-memory client so the test does not open a port. The server
class is ``MCPServer``. ``FastMCP`` was the name of this class in mcp 1.x.
"""

import asyncio
import json

from mcp import Client

from acp.credentials.auth import holder_proof_for
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


def test_read_credential_denies_without_holder_proof() -> None:
    server = build_server()

    async def _read(arguments: dict[str, str]) -> tuple[str, str]:
        async with Client(server) as client:
            try:
                result = await client.call_tool("read_credential", arguments)
            except Exception as exc:  # noqa: BLE001 — the SDK may raise or return isError
                return "error", str(exc)
            text = _result_text(result)
            if getattr(result, "is_error", False) or getattr(result, "isError", False):
                return "error", text
            return "ok", text

    arguments = {"credential_id": "vc-license-ada"}
    omitted_kind, omitted = asyncio.run(_read(arguments))
    empty_kind, empty = asyncio.run(_read({**arguments, "holder_proof": ""}))
    wrong = {**arguments, "holder_proof": "holder:did:example:other"}
    wrong_kind, wrong_body = asyncio.run(_read(wrong))
    proof = holder_proof_for(TEACHER_ADA)
    ok_kind, ok = asyncio.run(_read({**arguments, "holder_proof": proof}))

    assert omitted_kind == "error"
    assert empty_kind == "error"
    assert wrong_kind == "error"
    for body in (omitted, empty, wrong_body):
        assert "holder authentication required" in body
        assert ADA_HOME_ADDRESS not in body
    assert ok_kind == "ok"
    assert ADA_HOME_ADDRESS in ok


def _result_text(result: object) -> str:
    """Flatten whatever the SDK returned into text for a smoke assertion."""
    if hasattr(result, "model_dump"):
        return json.dumps(result.model_dump())
    return json.dumps(result, default=str)
