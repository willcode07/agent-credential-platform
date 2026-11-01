"""Smoke tests for the Agent Card and the JSON-RPC task handler."""

from fastapi.testclient import TestClient

from acp.app import create_app
from acp.protocols.a2a.card import RETIRED_AGENT_CARD_PATH
from acp.protocols.a2a.tasks import TaskService, handle_jsonrpc


def _message(text: str = "Find a math teacher") -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "SendMessage",
        "params": {
            "message": {
                "messageId": "msg-1",
                "role": "ROLE_USER",
                "parts": [{"text": text}],
            }
        },
    }


def test_agent_card_is_served_at_the_current_well_known_path() -> None:
    client = TestClient(create_app(base_url="http://127.0.0.1:8000"))
    response = client.get("/.well-known/agent-card.json")
    assert response.status_code == 200
    card = response.json()
    assert card["name"] == "ACP Matching Agent"
    assert card["version"] == "0.1.0"
    interface = card["supportedInterfaces"][0]
    assert interface["protocolBinding"] == "JSONRPC"
    assert interface["protocolVersion"] == "1.0"
    assert interface["url"] == "http://127.0.0.1:8000/a2a/v1"
    assert card["capabilities"]["streaming"] is False
    assert {skill["id"] for skill in card["skills"]} == {"match-teachers", "match-students"}
    retired = client.get(RETIRED_AGENT_CARD_PATH)
    assert retired.status_code == 404


def test_send_get_and_list_task_round_trip() -> None:
    client = TestClient(create_app())
    created = client.post("/a2a/v1", json=_message())
    assert created.status_code == 200
    body = created.json()
    task = body["result"]["task"]
    assert body["id"] == 1
    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    assert task["artifacts"][0]["parts"][0]["text"] == "Find a math teacher"

    fetched = client.post(
        "/a2a/v1",
        json={"jsonrpc": "2.0", "id": 2, "method": "GetTask", "params": {"id": task["id"]}},
    )
    assert fetched.json()["result"]["id"] == task["id"]

    listed = client.post(
        "/rpc",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "ListTasks",
            "params": {"includeArtifacts": False},
        },
    )
    page = listed.json()["result"]
    assert page["totalSize"] == 1
    assert page["nextPageToken"] == ""
    assert "artifacts" not in page["tasks"][0]


def test_unknown_method_and_missing_task() -> None:
    client = TestClient(create_app())
    unknown = client.post(
        "/a2a/v1",
        json={"jsonrpc": "2.0", "id": "x", "method": "message/send", "params": {}},
    )
    assert unknown.json()["error"]["code"] == -32601
    missing = client.post(
        "/a2a/v1",
        json={"jsonrpc": "2.0", "id": "y", "method": "GetTask", "params": {"id": "nope"}},
    )
    assert missing.json()["error"]["code"] == -32001


def test_streaming_is_unsupported_and_completed_tasks_are_not_cancelable() -> None:
    service = TaskService()
    response = service.send_message(_message()["params"])
    task_id = response["task"]["id"]
    unsupported = handle_jsonrpc(
        {"jsonrpc": "2.0", "id": 1, "method": "SendStreamingMessage", "params": {}},
        service,
    )
    assert unsupported["error"]["code"] == -32004
    denied = handle_jsonrpc(
        {"jsonrpc": "2.0", "id": 2, "method": "CancelTask", "params": {"id": task_id}},
        service,
    )
    assert denied["error"]["code"] == -32002

    stored = service.get_task({"id": task_id})
    stored["status"]["state"] = "TASK_STATE_WORKING"
    canceled = service.cancel_task({"id": task_id})
    assert canceled["status"]["state"] == "TASK_STATE_CANCELED"


def test_health() -> None:
    client = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok"}
