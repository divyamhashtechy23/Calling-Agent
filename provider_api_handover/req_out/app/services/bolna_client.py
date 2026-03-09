import httpx
import re

from app.config import settings
from app.schemas.call_start import CallStartRequest


def normalize_calling_script(script: str) -> str:
    lines = [line.strip("- ").strip() for line in script.splitlines() if line.strip()]
    if len(lines) <= 1 and script.strip():
        lines = [chunk.strip() for chunk in re.split(r"(?<=[.!?])\s+", script.strip()) if chunk.strip()]
    return "\n".join(f"STEP {idx}: {line}" for idx, line in enumerate(lines, start=1))


async def start_bolna_call(agent_id: str, payload: CallStartRequest) -> str:
    script = normalize_calling_script(payload.callingScript)

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{settings.BOLNA_BASE_URL}{settings.BOLNA_START_CALL_PATH}",
            headers={
                "Authorization": f"Bearer {settings.BOLNA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "agent_id": agent_id,
                "recipient_phone_number": payload.leadPhone,
                "user_data": {
                    "lead_name": payload.leadName,
                    "lead_phone": payload.leadPhone,
                    "lead_company": payload.leadCompany or "",
                    "caller_name": payload.callerName,
                    "org_name": payload.orgName,
                    "org_id": payload.orgId,
                    "sequence_id": payload.sequenceId,
                    "lead_id": payload.leadId,
                    "call_purpose": payload.callPurpose,
                    "calling_script": script,
                },
            },
        )
        response.raise_for_status()
        data = response.json()

    call_id = data.get("execution_id") or data.get("id")
    if not call_id:
        raise RuntimeError(f"Bolna start call response missing execution id: {data}")
    return call_id


async def fetch_execution(execution_id: str) -> dict:
    path = settings.BOLNA_EXECUTION_PATH_TEMPLATE.format(execution_id=execution_id)
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{settings.BOLNA_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {settings.BOLNA_API_KEY}"},
        )
        response.raise_for_status()
        return response.json()

