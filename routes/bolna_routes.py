"""
Bolna AI Routes — API endpoints for calling, webhooks, SIP trunks,
phone numbers, and provider management.
"""

import os
import json
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Response, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Call

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
from app.schemas import (
    InitiateCallRequest,
    ConnectSipTrunkRequest,
    BuyPhoneNumberRequest,
    ConnectProviderRequest,
    ScheduleBatchRequest,
)
from services.bolna_service import BolnaService, BolnaConfigError
from services.template_service import get_template

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Bolna AI"])

# Singleton BolnaService instance
_bolna_service: Optional[BolnaService] = None


def get_bolna_service() -> BolnaService:
    global _bolna_service
    if _bolna_service is None:
        _bolna_service = BolnaService()
    return _bolna_service


# ── Call Initiation ──────────────────────────────────────────────────── #

@router.post("/api/bolna/call", summary="Initiate a Bolna AI outbound call")
async def initiate_bolna_call(request: InitiateCallRequest):
    """Creates an outbound call via Bolna AI using the rich context payload."""

    db = SessionLocal()
    try:
        # Create DB record
        call = Call(
            lead_id=request.leadId,
            lead_name=request.leadName,
            lead_phone=request.leadPhone,
            status="initiated",
        )
        db.add(call)
        db.commit()
        db.refresh(call)

        # Build user_data for the AI agent context
        user_data = {
            "leadName": request.leadName,
            "leadCompany": request.leadCompany or "N/A",
            "callPurpose": request.callPurpose,
            "callingScript": request.callingScript,
            "callerName": request.callerName,
            "orgName": request.orgName,
        }

        # Metadata for internal tracking
        metadata = {
            "internal_call_id": call.id,
            "org_id": request.orgId,
            "user_id": request.userId,
            "sequence_id": request.sequenceId,
            "lead_id": request.leadId,
            "language": request.language,
        }

        # Call Bolna API
        try:
            service = get_bolna_service()
            bolna_response = service.initiate_call(
                to_number=request.leadPhone,
                agent_id=request.agent_id,
                from_number=request.from_number,
                metadata=metadata,
                user_data=user_data,
            )
        except BolnaConfigError as e:
            db.delete(call)
            db.commit()
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            call.status = "failed"
            db.commit()
            logger.error("Bolna call initiation failed: %s", e)
            raise HTTPException(status_code=502, detail=f"Bolna API error: {str(e)}")

        # Update DB with Bolna execution ID
        call.bolna_execution_id = bolna_response.get("execution_id") or bolna_response.get("id")
        call.status = bolna_response.get("status", "queued")
        db.commit()

        return {
            "success": True,
            "internal_call_id": call.id,
            "bolna_execution_id": call.bolna_execution_id,
            "status": call.status,
            "message": f"Call to {request.leadName} initiated successfully.",
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Failed to initiate call: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to initiate call: {str(e)}")
    finally:
        db.close()


# ── Webhook ──────────────────────────────────────────────────────────── #

@router.post("/webhook/bolna", summary="Bolna AI webhook — receives call events", status_code=204)
async def bolna_webhook(request: Request):
    """Bolna POSTs status updates here as the call progresses."""
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")

    try:
        data = json.loads(body_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    execution_id = data.get("execution_id") or data.get("id")
    status = data.get("status", "unknown")

    if not execution_id:
        logger.warning("Webhook received without execution_id")
        return Response(status_code=204)

    logger.info("Bolna webhook | execution_id=%s | status=%s", execution_id, status)

    db = SessionLocal()
    try:
        call = db.query(Call).filter(Call.bolna_execution_id == execution_id).first()
        if not call:
            logger.debug("No matching call for execution_id=%s", execution_id)
            return Response(status_code=204)

        if status == "in-progress":
            call.status = "ongoing"

        elif status == "call-disconnected":
            call.status = "ended"
            call.transcript = data.get("transcript")
            telephony = data.get("telephony_data") or {}
            duration_sec = telephony.get("duration") or data.get("conversation_time")
            if duration_sec:
                call.duration_ms = int(float(duration_sec) * 1000)

        elif status == "completed":
            call.status = "completed"

            if data.get("transcript") and not call.transcript:
                call.transcript = data.get("transcript")

            telephony = data.get("telephony_data") or {}
            call.recording_url = telephony.get("recording_url")

            duration_sec = telephony.get("duration") or data.get("conversation_time")
            if duration_sec and not call.duration_ms:
                call.duration_ms = int(float(duration_sec) * 1000)

            call.call_summary = data.get("summary") or data.get("call_summary")

            extracted = data.get("extracted_data") or {}
            if extracted:
                # Bolna sends values like "interest_level: medium" or "callback_requested: true"
                # We need to clean them — strip the key prefix and convert to proper types
                def clean_value(val):
                    """Extract the actual value from Bolna's 'key: value' string format."""
                    if not isinstance(val, str):
                        return val
                    # If it contains ":", take only the part after the last ":"
                    if ":" in val:
                        val = val.split(":")[-1].strip()
                    return val

                def to_bool(val):
                    """Convert string/bool to Python boolean for DB."""
                    if isinstance(val, bool):
                        return val
                    val = clean_value(val)
                    return str(val).lower() in ("true", "yes", "1")

                call.interest_level = clean_value(extracted.get("interest_level"))
                call.callback_requested = to_bool(extracted.get("callback_requested", False))
                call.callback_time = clean_value(extracted.get("callback_time"))
                call.stop_sequence = to_bool(extracted.get("stop_sequence", False))

            logger.info(
                "Call completed | execution_id=%s | interest=%s",
                execution_id, call.interest_level,
            )

        else:
            call.status = status
            logger.debug("Bolna status update: %s for %s", status, execution_id)

        db.commit()

    except Exception as e:
        logger.error("Webhook processing error: %s", e)
        db.rollback()
    finally:
        db.close()

    return Response(status_code=204)


# ── Call History ─────────────────────────────────────────────────────── #

@router.get("/api/bolna/calls", summary="List all Bolna AI calls")
async def list_bolna_calls(limit: int = 50):
    """Returns all calls initiated via Bolna, newest first."""
    db = SessionLocal()
    try:
        calls = (
            db.query(Call)
            .filter(Call.bolna_execution_id.isnot(None))
            .order_by(Call.created_at.desc())
            .limit(limit)
            .all()
        )
        return {
            "total": len(calls),
            "calls": [
                {
                    "id": c.id,
                    "bolna_execution_id": c.bolna_execution_id,
                    "lead_name": c.lead_name,
                    "lead_phone": c.lead_phone,
                    "status": c.status,
                    "duration_ms": c.duration_ms,
                    "has_transcript": bool(c.transcript),
                    "has_summary": bool(c.call_summary),
                    "recording_url": c.recording_url,
                    "interest_level": c.interest_level,
                    "callback_requested": c.callback_requested,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in calls
            ],
        }
    finally:
        db.close()


@router.get("/api/bolna/metrics", summary="Get overall calling performance metrics")
async def get_bolna_metrics():
    """Returns aggregated performance metrics for dashboard (total calls, duration, interest levels)."""
    db = SessionLocal()
    try:
        calls = db.query(Call).filter(Call.bolna_execution_id.isnot(None)).all()
        
        total_calls = len(calls)
        connected_calls = sum(1 for c in calls if c.status == "completed" or c.status == "ended")
        
        # Bolna returns duration in MS
        total_duration_ms = sum(c.duration_ms for c in calls if c.duration_ms)
        total_duration_minutes = round(total_duration_ms / 60000, 2)
        
        # Interest breakdown
        interest_stats = {
            "high": sum(1 for c in calls if str(c.interest_level).lower() == "high"),
            "medium": sum(1 for c in calls if str(c.interest_level).lower() == "medium"),
            "low": sum(1 for c in calls if str(c.interest_level).lower() == "low"),
            "unknown": sum(1 for c in calls if not c.interest_level or str(c.interest_level).lower() not in ["high", "medium", "low"])
        }
        
        return {
            "success": True,
            "metrics": {
                "total_calls": total_calls,
                "connected_calls": connected_calls,
                "connection_rate_pct": round((connected_calls / total_calls * 100), 1) if total_calls > 0 else 0,
                "total_duration_minutes": total_duration_minutes,
                "interest_breakdown": interest_stats,
            }
        }
    finally:
        db.close()


@router.get("/api/bolna/calls/{call_id}", summary="Get a Bolna AI call with full transcript")
async def get_bolna_call(call_id: str):
    """Retrieve a single call record by internal DB ID or Bolna execution ID."""
    db = SessionLocal()
    try:
        call = (
            db.query(Call).filter(Call.id == call_id).first()
            or db.query(Call).filter(Call.bolna_execution_id == call_id).first()
        )
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")

        return {
            "id": call.id,
            "bolna_execution_id": call.bolna_execution_id,
            "lead_id": call.lead_id,
            "lead_name": call.lead_name,
            "lead_phone": call.lead_phone,
            "status": call.status,
            "duration_ms": call.duration_ms,
            "transcript": call.transcript,
            "call_summary": call.call_summary,
            "recording_url": call.recording_url,
            "interest_level": call.interest_level,
            "callback_requested": call.callback_requested,
            "callback_time": call.callback_time,
            "stop_sequence": call.stop_sequence,
            "created_at": call.created_at.isoformat() if call.created_at else None,
        }
    finally:
        db.close()


# ── SIP Trunk Management ────────────────────────────────────────────── #

@router.post(
    "/api/bolna/sip-trunks",
    summary="Connect an external phone number via SIP trunk (BYOT)",
)
async def connect_sip_trunk(request: ConnectSipTrunkRequest):
    """Connect a business's SIP trunk phone number to Bolna."""
    try:
        if not request.phone_number.startswith("+") or len(request.phone_number) < 10:
            raise HTTPException(status_code=400, detail="Invalid phone number")

        service = get_bolna_service()
        result = service.create_sip_trunk(
            name=request.name,
            provider=request.provider,
            phone_number=request.phone_number,
            gateway_address=request.gateway_address,
            auth_type=request.auth_type,
            auth_username=request.auth_username,
            auth_password=request.auth_password,
        )
        return {
            "success": True,
            "message": f"Phone number {request.phone_number} connected to Bolna via SIP trunk.",
            "trunk_id": result.get("id") or result.get("trunk_id"),
            "phone_number": request.phone_number,
            "next_step": f"Use '{request.phone_number}' as from_number in POST /api/bolna/call",
        }

    except HTTPException:
        raise
    except BolnaConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("SIP trunk connection failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/api/bolna/sip-trunks",
    summary="List all connected SIP trunks",
)
async def list_sip_trunks():
    """Returns all SIP trunks connected to your Bolna account."""
    try:
        service = get_bolna_service()
        trunks = service.list_sip_trunks()
        return {
            "success": True,
            "count": len(trunks) if isinstance(trunks, list) else 0,
            "sip_trunks": trunks,
        }
    except Exception as e:
        logger.error("Failed to list SIP trunks: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@router.patch(
    "/api/bolna/sip-trunks/{trunk_id}",
    summary="Update a SIP trunk configuration",
)
async def update_sip_trunk(trunk_id: str, request: Request):
    """Update an existing SIP trunk configuration."""
    try:
        body = await request.json()
        service = get_bolna_service()
        result = service.update_sip_trunk(trunk_id, body)
        return {"success": True, "trunk": result}
    except Exception as e:
        logger.error("SIP trunk update failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


# ── Phone Number Management ─────────────────────────────────────────── #

@router.post(
    "/api/bolna/phone-numbers/buy",
    summary="Buy a phone number from Bolna",
)
async def buy_phone_number(request: BuyPhoneNumberRequest):
    """Buy a virtual phone number from Bolna."""
    try:
        service = get_bolna_service()
        result = service.buy_phone_number(
            country=request.country,
            phone_number=request.phone_number,
        )
        return {
            "success": True,
            "message": "Phone number purchased successfully.",
            "details": result,
        }
    except Exception as e:
        logger.error("Phone number purchase failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/api/bolna/phone-numbers/search",
    summary="Search available phone numbers",
)
async def search_phone_numbers(country: str = "IN"):
    """Search for available phone numbers by country."""
    try:
        service = get_bolna_service()
        numbers = service.search_phone_numbers(country=country)
        return {"success": True, "available_numbers": numbers}
    except Exception as e:
        logger.error("Phone number search failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/api/bolna/phone-numbers",
    summary="List all phone numbers on your Bolna account",
)
async def list_phone_numbers():
    """Returns all phone numbers linked to your Bolna account."""
    try:
        service = get_bolna_service()
        numbers = service.list_phone_numbers()
        return {
            "success": True,
            "count": len(numbers) if isinstance(numbers, list) else 0,
            "phone_numbers": numbers,
        }
    except Exception as e:
        logger.error("Failed to list phone numbers: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@router.delete(
    "/api/bolna/phone-numbers/{number_id}",
    summary="Delete a phone number from Bolna",
    status_code=200,
)
async def delete_phone_number(number_id: str):
    """Delete a phone number from your Bolna account."""
    try:
        service = get_bolna_service()
        service.delete_phone_number(number_id)
        return {
            "success": True,
            "message": f"Phone number {number_id} has been removed from Bolna.",
        }
    except Exception as e:
        logger.error("Phone number deletion failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


# ── Provider Management (alternative to SIP Trunk) ──────────────────── #

@router.get(
    "/api/bolna/providers/supported",
    summary="List all supported telephony providers",
)
async def list_supported_providers():
    """Returns the list of telephony providers we can connect."""
    providers = BolnaService.get_supported_providers()
    return {
        "success": True,
        "supported_providers": providers,
        "count": len(providers),
        "next_step": "Call GET /api/bolna/providers/fields/{provider} to see required fields",
    }


@router.get(
    "/api/bolna/providers/fields/{provider}",
    summary="Get required credential fields for a provider",
)
async def get_provider_fields(provider: str):
    """Returns the credential fields a business must provide for the given provider."""
    try:
        fields = BolnaService.get_required_fields(provider.lower())
        return {
            "success": True,
            "provider": provider.lower(),
            "required_fields": fields,
            "next_step": (
                f"Call POST /api/bolna/providers/connect with "
                f'{{"provider": "{provider.lower()}", "credentials": {{...}}}}'
            ),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/api/bolna/providers/connect",
    summary="Connect a business's telephony provider",
)
async def connect_provider(request: ConnectProviderRequest):
    """Connect a business's telephony provider credentials to Bolna."""
    try:
        service = get_bolna_service()
        result = service.connect_provider(
            provider=request.provider,
            credentials=request.credentials,
        )
        return {
            "success": True,
            "message": f"Provider '{request.provider}' connected successfully!",
            **result,
            "next_steps": [
                "Go to Bolna Dashboard → Agent → Call tab",
                f"Select '{request.provider}' as the telephony provider",
                "Select the phone number from the dropdown",
                "Click 'Save agent'",
                "Your calls will now go through the business's own number!",
            ],
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BolnaConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Provider connection failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/api/bolna/providers",
    summary="List all connected provider credentials",
)
async def list_providers():
    """Returns all provider credentials currently linked to Bolna (values masked)."""
    try:
        service = get_bolna_service()
        result = service.list_providers()
        return {
            "success": True,
            "providers": result,
        }
    except Exception as e:
        logger.error("Failed to list providers: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@router.delete(
    "/api/bolna/providers/{provider_id}",
    summary="Delete a single provider credential",
)
async def delete_provider(provider_id: str):
    """Delete a single provider credential from Bolna by its ID."""
    try:
        service = get_bolna_service()
        service.delete_provider(provider_id)
        return {
            "success": True,
            "message": f"Provider credential {provider_id} deleted.",
        }
    except Exception as e:
        logger.error("Provider deletion failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@router.delete(
    "/api/bolna/providers/disconnect/{provider}",
    summary="Disconnect a provider — removes ALL its credentials",
)
async def disconnect_provider(provider: str):
    """
    Remove ALL credentials for a given provider from Bolna.
    E.g. /disconnect/vobiz deletes VOBIZ_API_KEY, VOBIZ_API_SECRET,
    and VOBIZ_PHONE_NUMBER in one call.
    After disconnecting, you can reconnect with new credentials via
    POST /api/bolna/providers/connect.
    """
    try:
        service = get_bolna_service()
        result = service.disconnect_provider(provider)
        return {
            "success": True,
            "message": f"Provider '{provider}' disconnected — {result['credentials_deleted']} credentials removed.",
            **result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Provider disconnect failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))

# ── Batch ──────────────────────────────────────────────────────────── #

@router.post("/api/bolna/batches", summary="Create a batch call campaign from a CSV File")
async def create_batch(
    agent_id: Optional[str] = Form(None),
    template_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        csv_bytes = await file.read()
        service = get_bolna_service()

        template_data = None
        if template_id:
            db_template = get_template(db, temp_id=template_id)
            if not db_template:
                raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
                
            template_data = {
                "template_name": db_template.template_name,
                "industry": db_template.industry,
                "language": db_template.language,
                "org_name": db_template.org_name,
                "caller_name": db_template.caller_name,
                "call_purpose": db_template.call_purpose,
                "call_script": db_template.call_script
            }
            logger.info("Loaded template '%s' for batch", template_data["template_name"])

        result = service.create_batch(
            csv_bytes=csv_bytes,
            filename=file.filename,
            agent_id=agent_id,
            template_data=template_data
        )
        return {
            "success": True,
            "batch_id": result.get("batch_id") or result.get("id"),
            "message": f"Batch created from '{file.filename}'. Use batch_id to schedule or monitor.",
            "bolna_response": result,
        }

    except BolnaConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Batch creation failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
@router.post("/api/bolna/batches/{batch_id}/schedule", summary="Schedule a batch for a future date/time")
async def schedule_batch(batch_id: str, request: ScheduleBatchRequest):
    try:
        service = get_bolna_service()
        result = service.schedule_batch(
            batch_id=batch_id,
            scheduled_at=request.scheduled_at,
        )
        return {
            "success": True,
            "batch_id": batch_id,
            "scheduled_at": request.scheduled_at,
            "bolna_response": result,
        }
    except Exception as e:
        logger.error("Batch scheduling failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/api/bolna/batches", summary="List all batch call campaigns")
async def list_batches():
    try:
        service = get_bolna_service()
        result = service.list_batches()
        return {"success": True, "batches": result}
    except Exception as e:
        logger.error("Failed to list batches: %s", e)
        raise HTTPException(status_code=502, detail=str(e))

@router.get("/api/bolna/batches/{batch_id}", summary="Get status and progress of a batch")
async def get_batch(batch_id: str):
    try:
        service = get_bolna_service()
        result = service.get_batch(batch_id)
        return {"success": True, "batch": result}
    except Exception as e:
        logger.error("Failed to get batch: %s", e)
        raise HTTPException(status_code=502, detail=str(e))

@router.post("/api/bolna/batches/{batch_id}/stop", summary="Stop an active batch campaign")
async def stop_batch(batch_id: str):
    try:
        service = get_bolna_service()
        result = service.stop_batch(batch_id)
        return {
            "success": True,
            "batch_id": batch_id,
            "message": "Batch stop requested successfully.",
            "bolna_response": result,
        }
    except Exception as e:
        logger.error("Failed to stop batch: %s", e)
        raise HTTPException(status_code=502, detail=str(e))

@router.get("/api/bolna/batches/{batch_id}/executions", summary="Get all executions for a batch")
async def get_batch_executions(batch_id: str):
    try:
        service = get_bolna_service()
        result = service.get_batch_executions(batch_id)
        return {"success": True,"batch_id":batch_id,"executions": result}
    except Exception as e:
        logger.error("Failed to get batch executions: %s", e)
        raise HTTPException(status_code=502, detail=str(e))