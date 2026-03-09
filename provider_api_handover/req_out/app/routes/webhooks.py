from fastapi import APIRouter, Request
import json

from app.config import settings
from app.services.bolna_normalizer import normalize_bolna_execution
from app.services.call_state import upsert_call_state, clear_call_state
from app.services.notifier import send_to_crm
from app.utils.idempotency import clear_active, make_key

router = APIRouter()


@router.post("/bolna/execution")
async def bolna_execution_webhook(request: Request):
    if settings.BOLNA_WEBHOOK_SECRET:
        if request.headers.get("x-bolna-secret", "") != settings.BOLNA_WEBHOOK_SECRET:
            return {"status": "ignored", "reason": "invalid signature"}

    payload = await request.json()

    print("\n===== BOLNA WEBHOOK RECEIVED =====")
    print(json.dumps(payload, indent=2))
    print("==================================\n")

    normalized = normalize_bolna_execution(payload)
    execution_id = normalized.get("callId")
    call_state = normalized.get("callState")

    if execution_id:
        upsert_call_state(execution_id, normalized)

    if call_state not in ("completed", "failed"):
        return {"status": "ignored", "reason": f"callState={call_state}"}

    if execution_id:
        clear_active(execution_id)

    org_id = normalized.get("orgId")
    sequence_id = normalized.get("sequenceId")
    lead_id = normalized.get("leadId")
    if org_id and sequence_id and lead_id:
        clear_active(make_key(org_id, sequence_id, lead_id))

    await send_to_crm(normalized)
    if execution_id:
        clear_call_state(execution_id)

    return {"status": "delivered", "callId": execution_id}

