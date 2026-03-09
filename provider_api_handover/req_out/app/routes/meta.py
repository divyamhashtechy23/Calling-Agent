from fastapi import APIRouter
from app.utils.idempotency import make_key, clear_active

router = APIRouter()

@router.post("/webhooks/ai-calls/result")
async def receive_call_result(payload: dict):
    metadata = payload.get("metadata") or {}
    org_id = payload.get("orgId") or metadata.get("org_id")
    sequence_id = payload.get("sequenceId") or metadata.get("sequence_id")
    lead_id = payload.get("leadId") or metadata.get("lead_id")

    if org_id and sequence_id and lead_id:
        clear_active(make_key(org_id, sequence_id, lead_id))

    print("Webhook received:", payload)

    return {"status": "received"}
