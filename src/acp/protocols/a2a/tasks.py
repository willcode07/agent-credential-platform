"""Minimal A2A task handler (JSON-RPC binding, spec 1.0.0).

Implemented methods: ``SendMessage``, ``GetTask``, ``ListTasks``, ``CancelTask``.
Streaming, push notifications, and the extended card return
``UnsupportedOperationError`` (-32004) so a client can tell "not built" from
"unknown method" (-32601).

Field names are camelCase and task states use the proto enum strings
(``TASK_STATE_COMPLETED``, and so on), as required by spec section 5.5.

The handler records a task and completes it immediately. It does not call
the matcher; the demo submits a finished summary as the user message.

# OPEN QUESTION: tasks are stored in process memory. What is the retention
# and tenancy model once more than one school shares an agent?
"""

from collections import OrderedDict
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

TASK_NOT_FOUND = -32001
TASK_NOT_CANCELABLE = -32002
UNSUPPORTED_OPERATION = -32004
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602

_TERMINAL = {
    "TASK_STATE_COMPLETED",
    "TASK_STATE_FAILED",
    "TASK_STATE_CANCELED",
    "TASK_STATE_REJECTED",
}
_PART_KEYS = ("text", "raw", "url", "data")
_UNIMPLEMENTED = {
    "SendStreamingMessage",
    "SubscribeToTask",
    "CreateTaskPushNotificationConfig",
    "GetTaskPushNotificationConfig",
    "ListTaskPushNotificationConfigs",
    "DeleteTaskPushNotificationConfig",
    "GetExtendedAgentCard",
}


class TaskService:
    """In-memory tasks for one process."""

    def __init__(self) -> None:
        self._tasks: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def send_message(self, params: dict[str, Any]) -> dict[str, Any]:
        message = params.get("message")
        if not isinstance(message, dict):
            raise InvalidParams("SendMessage requires params.message")
        _require_message(message)
        task_id = str(uuid4())
        context_id = message.get("contextId") or str(uuid4())
        now = _now()
        text = _message_text(message)
        user_message = {
            "messageId": message["messageId"],
            "contextId": context_id,
            "taskId": task_id,
            "role": message["role"],
            "parts": message["parts"],
        }
        summary = text if text else "Structured message recorded."
        agent_message = _agent_message(
            context_id,
            task_id,
            f"Recorded: {summary}",
        )
        artifact = {
            "artifactId": str(uuid4()),
            "name": "result",
            "parts": [{"text": summary}],
        }
        task = {
            "id": task_id,
            "contextId": context_id,
            "status": {
                "state": "TASK_STATE_COMPLETED",
                "message": agent_message,
                "timestamp": now,
            },
            "artifacts": [artifact],
            "history": [user_message, agent_message],
        }
        self._tasks[task_id] = task
        return {"task": task}

    def get_task(self, params: dict[str, Any]) -> dict[str, Any]:
        task = self._require(params)
        return _apply_history_length(task, params.get("historyLength"))

    def list_tasks(self, params: dict[str, Any]) -> dict[str, Any]:
        page_size = params.get("pageSize", 50)
        if not isinstance(page_size, int) or not 1 <= page_size <= 100:
            raise InvalidParams("pageSize must be an integer from 1 to 100")
        offset = _page_offset(params.get("pageToken"))
        context_id = params.get("contextId")
        status = params.get("status")
        matched = [
            task
            for task in self._tasks.values()
            if (context_id is None or task["contextId"] == context_id)
            and (status is None or task["status"]["state"] == status)
        ]
        page = matched[offset : offset + page_size]
        include_artifacts = bool(params.get("includeArtifacts", False))
        tasks = []
        for task in page:
            view = _apply_history_length(task, params.get("historyLength"))
            if not include_artifacts:
                view.pop("artifacts", None)
            tasks.append(view)
        next_offset = offset + len(page)
        next_token = "" if next_offset >= len(matched) else str(next_offset)
        return {
            "tasks": tasks,
            "nextPageToken": next_token,
            "pageSize": page_size,
            "totalSize": len(matched),
        }

    def cancel_task(self, params: dict[str, Any]) -> dict[str, Any]:
        task = self._require(params)
        state = task["status"]["state"]
        if state in _TERMINAL:
            raise TaskNotCancelable(task["id"])
        task["status"] = {
            "state": "TASK_STATE_CANCELED",
            "timestamp": _now(),
        }
        return task

    def _require(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id = params.get("id")
        if not isinstance(task_id, str) or not task_id:
            raise InvalidParams("id is required")
        task = self._tasks.get(task_id)
        if task is None:
            raise TaskNotFound(task_id)
        return task


class TaskError(Exception):
    code = INVALID_PARAMS

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidParams(TaskError):
    code = INVALID_PARAMS


class TaskNotFound(TaskError):
    code = TASK_NOT_FOUND

    def __init__(self, task_id: str) -> None:
        super().__init__(f"Task not found: {task_id}")


class TaskNotCancelable(TaskError):
    code = TASK_NOT_CANCELABLE

    def __init__(self, task_id: str) -> None:
        super().__init__(f"Task cannot be canceled: {task_id}")


def handle_jsonrpc(payload: Any, tasks: TaskService) -> dict[str, Any]:
    """Dispatch one JSON-RPC 2.0 request. Always returns a response object."""
    if not isinstance(payload, dict):
        return _error(None, INVALID_REQUEST, "JSON-RPC request must be an object")
    request_id = payload.get("id")
    if payload.get("jsonrpc") != "2.0" or "method" not in payload:
        return _error(request_id, INVALID_REQUEST, "jsonrpc must be '2.0' and method is required")
    method = payload["method"]
    params = payload.get("params") or {}
    if not isinstance(method, str) or not isinstance(params, dict):
        return _error(request_id, INVALID_REQUEST, "method must be a string and params an object")
    if method in _UNIMPLEMENTED:
        return _error(
            request_id,
            UNSUPPORTED_OPERATION,
            f"{method} is not implemented on this placeholder",
        )
    handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
        "SendMessage": tasks.send_message,
        "GetTask": tasks.get_task,
        "ListTasks": tasks.list_tasks,
        "CancelTask": tasks.cancel_task,
    }
    handler = handlers.get(method)
    if handler is None:
        return _error(request_id, METHOD_NOT_FOUND, f"Method not found: {method}")
    try:
        result = handler(params)
    except TaskError as exc:
        return _error(request_id, exc.code, exc.message)
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _require_message(message: dict[str, Any]) -> None:
    if message.get("role") != "ROLE_USER":
        raise InvalidParams("message.role must be ROLE_USER")
    if not isinstance(message.get("messageId"), str) or not message["messageId"]:
        raise InvalidParams("message.messageId is required")
    parts = message.get("parts")
    if not isinstance(parts, list) or not parts:
        raise InvalidParams("message.parts must be a non-empty array")
    for part in parts:
        if not isinstance(part, dict):
            raise InvalidParams("each part must be an object")
        present = [key for key in _PART_KEYS if key in part]
        if len(present) != 1:
            raise InvalidParams("each part must set exactly one of text, raw, url, data")


def _message_text(message: dict[str, Any]) -> str:
    chunks: list[str] = []
    for part in message["parts"]:
        if "text" in part and isinstance(part["text"], str):
            chunks.append(part["text"])
    return "\n".join(chunks).strip()


def _agent_message(context_id: str, task_id: str, text: str) -> dict[str, Any]:
    return {
        "messageId": str(uuid4()),
        "contextId": context_id,
        "taskId": task_id,
        "role": "ROLE_AGENT",
        "parts": [{"text": text}],
    }


def _apply_history_length(task: dict[str, Any], history_length: Any) -> dict[str, Any]:
    view = dict(task)
    if history_length is None:
        return view
    if not isinstance(history_length, int) or history_length < 0:
        raise InvalidParams("historyLength must be a non-negative integer")
    if history_length == 0:
        view.pop("history", None)
        return view
    history = list(task.get("history") or [])
    view["history"] = history[-history_length:]
    return view


def _page_offset(page_token: Any) -> int:
    if page_token in (None, ""):
        return 0
    if not isinstance(page_token, str) or not page_token.isdigit():
        raise InvalidParams("pageToken is not recognized")
    return int(page_token)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
