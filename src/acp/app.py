"""FastAPI surface: health, the A2A Agent Card, and the JSON-RPC task endpoint."""

from fastapi import FastAPI

from acp import __version__
from acp.protocols.a2a.card import (
    AGENT_CARD_WELL_KNOWN_PATH,
    JSONRPC_ALIAS_PATH,
    JSONRPC_PATH,
    build_agent_card,
)
from acp.protocols.a2a.tasks import TaskService, handle_jsonrpc


def create_app(base_url: str = "http://127.0.0.1:8000") -> FastAPI:
    """Build the app. ``base_url`` is written into the Agent Card interface URL."""
    app = FastAPI(
        title="Agent Credential Platform",
        version=__version__,
        summary="Privacy-preserving credential verification and matching.",
    )
    tasks = TaskService()
    card = build_agent_card(base_url)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get(AGENT_CARD_WELL_KNOWN_PATH)
    def agent_card() -> dict[str, object]:
        return card

    @app.post(JSONRPC_PATH)
    def jsonrpc(body: dict) -> dict:
        return handle_jsonrpc(body, tasks)

    @app.post(JSONRPC_ALIAS_PATH)
    def jsonrpc_alias(body: dict) -> dict:
        # Spec section 9.2 writes the binding example as POST /rpc.
        # The path is not registered; the card's supportedInterfaces URL is.
        return handle_jsonrpc(body, tasks)

    return app


app = create_app()
