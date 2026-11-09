"""WebSocket node protocol for Android/web/desktop clients."""

import json
import uuid
from typing import Any, Dict, Optional


def new_request_id() -> str:
    return uuid.uuid4().hex


def build_message(kind: str, payload: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None) -> str:
    return json.dumps({
        "kind": kind,
        "request_id": request_id or new_request_id(),
        "payload": payload or {},
    })


def validate_message(raw: str) -> Dict[str, Any]:
    try:
        obj = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid json: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError("message must be an object")
    if "kind" not in obj:
        raise ValueError("missing 'kind'")
    if "request_id" not in obj:
        obj["request_id"] = new_request_id()
    if "payload" not in obj or not isinstance(obj["payload"], dict):
        obj["payload"] = {}
    return obj


class NodeProtocol:
    """Lightweight request/response correlation helper."""

    def __init__(self):
        self._pending: Dict[str, Any] = {}

    def register(self, request_id: str, future) -> None:
        self._pending[request_id] = future

    def resolve(self, request_id: str, result: Any) -> bool:
        fut = self._pending.pop(request_id, None)
        if fut is None:
            return False
        try:
            fut.set_result(result)
        except Exception:
            pass
        return True

    def drop(self, request_id: str) -> None:
        self._pending.pop(request_id, None)

    def pending_count(self) -> int:
        return len(self._pending)

