"""Command line: ``acp serve``, ``acp mcp``, ``acp demo``."""

import argparse

from acp.demo import run_demo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="acp",
        description="Agent Credential Platform",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Run the FastAPI app (Agent Card and A2A tasks)")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    mcp_cmd = sub.add_parser("mcp", help="Run the mock MCP credential store")
    mcp_cmd.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="stdio is what local MCP hosts launch; streamable-http listens on a port",
    )
    mcp_cmd.add_argument("--host", default="127.0.0.1")
    mcp_cmd.add_argument("--port", type=int, default=8001)

    sub.add_parser("demo", help="Run the education example (schools, teachers, students)")

    args = parser.parse_args(argv)
    if args.command == "serve":
        return _serve(args.host, args.port)
    if args.command == "mcp":
        return _mcp(args.transport, args.host, args.port)
    return _demo()


def _serve(host: str, port: int) -> int:
    import uvicorn

    from acp.app import create_app

    # OPEN QUESTION: behind a reverse proxy this origin is not the public URL
    # that should be written into the Agent Card.
    uvicorn.run(create_app(base_url=f"http://{host}:{port}"), host=host, port=port)
    return 0


def _mcp(transport: str, host: str, port: int) -> int:
    from acp.protocols.mcp.server import build_server

    server = build_server()
    if transport == "stdio":
        server.run(transport="stdio")
        return 0
    server.run(transport="streamable-http", host=host, port=port)
    return 0


def _demo() -> int:
    print(run_demo().text)
    return 0
