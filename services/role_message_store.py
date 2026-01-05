# services/role_message_store.py
import json
import os

ROLE_STATE_FILE = "role_state.json"


def _load() -> dict:
    if not os.path.exists(ROLE_STATE_FILE):
        return {}
    try:
        with open(ROLE_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _save(d: dict) -> None:
    with open(ROLE_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def load_role_message_id(state_key: str) -> int | None:
    d = _load()
    v = d.get(state_key)
    return int(v) if v else None


def save_role_message_id(state_key: str, msg_id: int) -> None:
    d = _load()
    d[state_key] = msg_id
    _save(d)
