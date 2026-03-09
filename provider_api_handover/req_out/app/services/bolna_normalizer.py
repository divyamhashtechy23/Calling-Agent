from datetime import datetime, timezone

from app.services.call_state import map_call_state


def normalize_bolna_execution(payload: dict) -> dict:
    telephony = payload.get("telephony_data") or {}
    extracted = payload.get("extracted_data") or {}
    context = payload.get("context_details") or {}
    recipient = context.get("recipient_data") or {}
    call_state = map_call_state(payload.get("status"))
    event_type = "call.completed" if call_state == "completed" else "call.failed" if call_state == "failed" else "call.updated"

    return {
        "eventType": event_type,
        "callId": payload.get("id") or payload.get("execution_id"),
        "callState": call_state,
        "orgId": recipient.get("org_id"),
        "sequenceId": recipient.get("sequence_id"),
        "leadId": recipient.get("lead_id"),
        "timestamps": {
            "initiatedAt": payload.get("initiated_at"),
            "completedAt": payload.get("completed_at") or datetime.now(timezone.utc).isoformat(),
        },
        "metrics": {
            "durationSeconds": payload.get("conversation_duration"),
            "totalCost": payload.get("total_cost"),
        },
        "outcome": {
            "interestLevel": extracted.get("interest_level"),
            "callbackRequested": str(extracted.get("callback_requested", "")).lower() == "true",
            "callbackTime": extracted.get("callback_time"),
            "stopSequence": str(extracted.get("stop_sequence", "")).lower() == "true",
            "notes": extracted.get("notes"),
        },
        "artifacts": {
            "transcript": payload.get("transcript"),
            "summary": payload.get("summary"),
            "recordingUrl": telephony.get("recording_url"),
        },
        "provider": {
            "name": "bolna",
            "telephony": payload.get("provider"),
            "agentId": payload.get("agent_id"),
            "providerCallId": telephony.get("provider_call_id"),
            "hangupReason": telephony.get("hangup_reason"),
        },
        "raw": payload,
    }

