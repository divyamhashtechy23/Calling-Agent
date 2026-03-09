import httpx
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone

from app.auth import verify_api_key
from app.schemas.call_start import CallStartRequest
from app.schemas.call_result import CallStartResponse
from app.services.agent_registry import get_agent_id
from app.services.bolna_client import start_bolna_call, fetch_execution
from app.services.bolna_normalizer import normalize_bolna_execution
from app.utils.idempotency import make_key, is_active, mark_active

router = APIRouter()


# =====================================
# Start AI call (COMMAND)
# =====================================
@router.post("/start", response_model=CallStartResponse)
async def start_call(
    payload: CallStartRequest,
    _=Depends(verify_api_key)
):
    idem_key = make_key(
        payload.orgId,
        payload.sequenceId,
        payload.leadId
    )

    if is_active(idem_key):
        return CallStartResponse(
            callId="",
            status="already-running",
            orgId=payload.orgId,
            sequenceId=payload.sequenceId,
            leadId=payload.leadId,
            timestamp=datetime.now(timezone.utc)
        )

    agent_id = get_agent_id(payload.language)

    try:
        call_id = await start_bolna_call(
            agent_id=agent_id,
            payload=payload
        )
    except httpx.HTTPStatusError as exc:
        upstream_status = exc.response.status_code if exc.response else None
        upstream_body = exc.response.text if exc.response else ""
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Bolna start call failed",
                "upstreamStatus": upstream_status,
                "upstreamBody": upstream_body[:1000],
            },
        ) from exc

    mark_active(idem_key)

    return CallStartResponse(
        callId=call_id,
        status="started",
        orgId=payload.orgId,
        sequenceId=payload.sequenceId,
        leadId=payload.leadId,
        timestamp=datetime.now(timezone.utc)
    )


# =====================================
# Fetch execution details (QUERY / FALLBACK)
# =====================================
@router.get("/{execution_id}")
async def get_call_execution(
    execution_id: str,
    _=Depends(verify_api_key)
):
    raw = await fetch_execution(execution_id)
    return normalize_bolna_execution(raw)
