# app/services/call_state.py

from typing import Dict


CALL_STATE: Dict[str, dict] = {}


def map_call_state(provider_status: str) -> str:
    if not provider_status:
        return "unknown"

    provider_status = provider_status.lower().replace("-", "_")

    if provider_status in ("initiated", "queued", "ringing"):
        return "initiated"

    if provider_status in ("in_progress", "inprogress", "ongoing"):
        return "in_progress"

    if provider_status in ("completed", "call_disconnected", "ended", "done"):
        return "completed"

    if provider_status in ("failed", "error", "cancelled", "canceled", "no_answer", "busy"):
        return "failed"

    return "unknown"


def upsert_call_state(execution_id: str, payload: dict):
    CALL_STATE[execution_id] = payload


def get_call_state(execution_id: str):
    return CALL_STATE.get(execution_id)


def clear_call_state(execution_id: str):
    CALL_STATE.pop(execution_id, None)
