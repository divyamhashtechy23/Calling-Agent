from datetime import datetime, timedelta, timezone

from app.config import settings


# TEMP in-memory store (safe for now).
# Store lock timestamp so stale locks auto-expire if webhooks are missed.
_active_calls: dict[str, datetime] = {}


def _ttl_seconds() -> int:
    # Defensive guard in case env value is zero/negative.
    return max(1, settings.IDEMPOTENCY_TTL_SECONDS)


def _is_expired(marked_at: datetime) -> bool:
    return datetime.now(timezone.utc) - marked_at > timedelta(seconds=_ttl_seconds())


def _prune_if_expired(key: str):
    marked_at = _active_calls.get(key)
    if marked_at and _is_expired(marked_at):
        _active_calls.pop(key, None)


def make_key(org_id: str, sequence_id: str, lead_id: str) -> str:
    return f"{org_id}:{sequence_id}:{lead_id}"


def is_active(key: str) -> bool:
    _prune_if_expired(key)
    return key in _active_calls


def mark_active(key: str):
    _active_calls[key] = datetime.now(timezone.utc)


def clear_active(key: str):
    _active_calls.pop(key, None)
