from __future__ import annotations
from core.user_paths import get_user_data_dir

import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet


def _base_dir() -> Path:
    return Path(__file__).resolve().parent.parent


BASE_DIR = _base_dir()
CONFIG_DIR = get_user_data_dir() / "config"
DB_FILE = CONFIG_DIR / "smart_home.sqlite3"
KEY_FILE = CONFIG_DIR / "smart_home.key"


def _ensure_dir() -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)


def _now_ms() -> int:
    return int(time.time() * 1000)


class CredentialVault:
    def __init__(self, key_file: Path = KEY_FILE):
        _ensure_dir()
        self._key_file = key_file
        self._fernet = Fernet(self._load_or_create_key())

    def _load_or_create_key(self) -> bytes:
        if self._key_file.exists():
            return self._key_file.read_bytes().strip()
        key = Fernet.generate_key()
        self._key_file.write_bytes(key)
        return key

    def encrypt_json(self, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        return self._fernet.encrypt(raw).decode("utf-8")

    def decrypt_json(self, payload: str | None) -> dict[str, Any]:
        if not payload:
            return {}
        try:
            data = self._fernet.decrypt(payload.encode("utf-8"))
            obj = json.loads(data.decode("utf-8"))
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}


class SmartHomeStorage:
    def __init__(self, db_path: Path | None = None):
        _ensure_dir()
        self._db_path = Path(db_path or DB_FILE)
        self._lock = threading.RLock()
        self._vault = CredentialVault()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS provider_accounts (
                    id TEXT PRIMARY KEY,
                    provider_key TEXT NOT NULL,
                    account_label TEXT NOT NULL,
                    credentials_encrypted TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    provider_account_id TEXT NOT NULL,
                    provider_key TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    manufacturer TEXT NOT NULL,
                    room TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    image_key TEXT NOT NULL,
                    is_on INTEGER NOT NULL DEFAULT 0,
                    traits_json TEXT NOT NULL DEFAULT '{}',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    UNIQUE(provider_account_id, external_id)
                );

                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    detail TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS scenes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                """
            )

    def save_provider_account(self, provider_key: str, account_label: str, credentials: dict[str, Any]) -> str:
        account_id = str(uuid.uuid4())
        stamp = _now_ms()
        enc = self._vault.encrypt_json(credentials)
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM provider_accounts WHERE provider_key = ? AND account_label = ?",
                (provider_key, account_label),
            ).fetchone()
            if row:
                account_id = row["id"]
                conn.execute(
                    """
                    UPDATE provider_accounts
                    SET credentials_encrypted = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (enc, stamp, account_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO provider_accounts(id, provider_key, account_label, credentials_encrypted, created_at, updated_at)
                    VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (account_id, provider_key, account_label, enc, stamp, stamp),
                )
        return account_id

    def get_provider_account(self, account_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM provider_accounts WHERE id = ?", (account_id,)).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "provider_key": row["provider_key"],
            "account_label": row["account_label"],
            "credentials": self._vault.decrypt_json(row["credentials_encrypted"]),
            "created_at": int(row["created_at"]),
            "updated_at": int(row["updated_at"]),
        }

    def save_devices(self, provider_account_id: str, provider_key: str, devices: list[dict[str, Any]]) -> list[str]:
        stamp = _now_ms()
        saved: list[str] = []
        with self._lock, self._connect() as conn:
            for device in devices:
                row = conn.execute(
                    "SELECT id FROM devices WHERE provider_account_id = ? AND external_id = ?",
                    (provider_account_id, str(device["external_id"])),
                ).fetchone()
                device_id = row["id"] if row else str(uuid.uuid4())
                payload = json.dumps(device.get("traits", {}), ensure_ascii=True)
                if row:
                    conn.execute(
                        """
                        UPDATE devices
                        SET name = ?, manufacturer = ?, room = ?, device_type = ?, image_key = ?, is_on = ?, traits_json = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            str(device["name"]),
                            str(device.get("manufacturer", "")),
                            str(device.get("room", "Unassigned")),
                            str(device.get("device_type", "device")),
                            str(device.get("image_key", "device")),
                            1 if bool(device.get("is_on")) else 0,
                            payload,
                            stamp,
                            device_id,
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO devices(id, provider_account_id, provider_key, external_id, name, manufacturer, room, device_type, image_key, is_on, traits_json, created_at, updated_at)
                        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            device_id,
                            provider_account_id,
                            provider_key,
                            str(device["external_id"]),
                            str(device["name"]),
                            str(device.get("manufacturer", "")),
                            str(device.get("room", "Unassigned")),
                            str(device.get("device_type", "device")),
                            str(device.get("image_key", "device")),
                            1 if bool(device.get("is_on")) else 0,
                            payload,
                            stamp,
                            stamp,
                        ),
                    )
                saved.append(device_id)
        return saved

    def list_devices(self, search: str = "", room: str = "") -> list[dict[str, Any]]:
        where: list[str] = []
        params: list[Any] = []
        if search:
            like = f"%{search.strip()}%"
            where.append("(name LIKE ? OR manufacturer LIKE ? OR room LIKE ?)")
            params.extend([like, like, like])
        if room:
            where.append("room = ?")
            params.append(room)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        query = f"""
            SELECT d.*, p.account_label
            FROM devices d
            JOIN provider_accounts p ON p.id = d.provider_account_id
            {where_sql}
            ORDER BY d.updated_at DESC, d.created_at DESC
        """
        with self._lock, self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            traits = {}
            try:
                traits = json.loads(row["traits_json"]) if row["traits_json"] else {}
            except Exception:
                traits = {}
            result.append(
                {
                    "id": row["id"],
                    "provider_account_id": row["provider_account_id"],
                    "provider_key": row["provider_key"],
                    "account_label": row["account_label"],
                    "external_id": row["external_id"],
                    "name": row["name"],
                    "manufacturer": row["manufacturer"],
                    "room": row["room"],
                    "device_type": row["device_type"],
                    "image_key": row["image_key"],
                    "is_on": bool(row["is_on"]),
                    "traits": traits,
                    "created_at": int(row["created_at"]),
                    "updated_at": int(row["updated_at"]),
                }
            )
        return result

    def get_device(self, device_id: str) -> dict[str, Any] | None:
        items = self.list_devices()
        for item in items:
            if item["id"] == device_id:
                return item
        return None

    def update_device(self, device_id: str, *, name: str | None = None, room: str | None = None,
                      is_on: bool | None = None, traits: dict[str, Any] | None = None) -> None:
        current = self.get_device(device_id)
        if not current:
            return
        merged_traits = dict(current.get("traits") or {})
        if traits:
            merged_traits.update(traits)
        payload = json.dumps(merged_traits, ensure_ascii=True)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE devices
                SET name = ?, room = ?, is_on = ?, traits_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    name or current["name"],
                    room or current["room"],
                    1 if (current["is_on"] if is_on is None else bool(is_on)) else 0,
                    payload,
                    _now_ms(),
                    device_id,
                ),
            )

    def forget_device(self, device_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM devices WHERE id = ?", (device_id,))

    def log_activity(self, title: str, detail: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO activities(created_at, title, detail) VALUES(?, ?, ?)",
                (_now_ms(), title, detail),
            )

    def recent_activity(self, limit: int = 10) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT created_at, title, detail FROM activities ORDER BY created_at DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
        return [
            {"created_at": int(row["created_at"]), "title": row["title"], "detail": row["detail"]}
            for row in rows
        ]

    def count_devices(self) -> int:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM devices").fetchone()
        return int(row["c"]) if row else 0


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_count_devices(kwargs: dict) -> dict:
    storage = SmartHomeStorage()
    return _op("count_devices", True, {"count": storage.count_devices()})


def _op_list_devices(kwargs: dict) -> dict:
    storage = SmartHomeStorage()
    return _op("list_devices", True, {"devices": storage.list_devices(), "total": len(storage.list_devices())})


def _op_recent_activity(kwargs: dict) -> dict:
    storage = SmartHomeStorage()
    limit = int(kwargs.get("limit", 10))
    return _op("recent_activity", True, {"activities": storage.recent_activity(limit), "total": len(storage.recent_activity(limit))})


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["smart_home_storage"],
        "content": "Smart home storage layer (SQLite + Fernet encryption).",
    })


_OPERATIONS = {
    "count_devices": _op_count_devices,
    "list_devices": _op_list_devices,
    "recent_activity": _op_recent_activity,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "count_devices": "Count Devices",
    "list_devices": "List Devices",
    "recent_activity": "Recent Activity",
    "sources": "Storage Sources",
}

_ALIASES = {
    "count": "count_devices",
    "devices": "list_devices",
    "activity": "recent_activity",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "count_devices":
        return f"{value.get('count')} device(s) in storage."
    if operation == "list_devices":
        return f"{value.get('total')} device(s) listed."
    if operation == "recent_activity":
        return f"{value.get('total')} recent activity(ies)."
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Smart home storage layer for encrypted credential storage and device management."""
    operation = (kwargs.get("operation") or "count_devices").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Smart Home Storage",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Smart Home Storage",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Smart Home Storage",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Storage error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Smart Home Storage"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="count_devices"))
