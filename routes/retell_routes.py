"""
Retell AI Routes

POST /api/retell/call          — initiate an outbound call
GET  /api/retell/calls         — list all Retell calls
GET  /api/retell/calls/{id}    — get one call with full transcript

POST /webhook/retell           — Retell event webhook (call_started, call_ended, call_analyzed)
"""

import os
import json
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Response
from retell import Retell

from app.database import SessionLocal
from app.models import Call
from app.schemas import (
    InitiateCallRequest,
    WebCallRequest,
    ImportPhoneNumberRequest,
)
from services.retell_service import RetellService, RetellConfigError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Retell AI"])

# ------------------------------------------------------------------ #
#   Singleton RetellService                                            #
# ------------------------------------------------------------------ #

_retell_service: Optional[RetellService] = None


def get_retell_service() -> RetellService:
    global _retell_service
    if _retell_service is None:
        _retell_service = RetellService()
    return _retell_service


# ------------------------------------------------------------------ #
#   POST /api/retell/call — initiate outbound call                    #
# ------------------------------------------------------------------ #


# ------------------------------------------------------------------ #
#   POST /api/retell/call — initiate outbound call                    #
# ------------------------------------------------------------------ #

@router.post("/api/retell/call", summary="Initiate a Retell AI outbound call")
async def initiate_retell_call(request: InitiateCallRequest):
    """
    Creates an outbound call via Retell AI.
    Retell handles the full STT → LLM → TTS conversation using your pre-built agent.
    The call record is saved to the database and fields are updated via the /webhook/retell endpoint.
    """
    db = SessionLocal()
    try:
        # 1. Create a DB record immediately so we can track before webhook fires
        call = Call(
            lead_id=request.lead_id or "N/A",
            lead_name=request.lead_name or "Unknown",
            lead_phone=request.to_number,
            status="initiated",
        )
        db.add(call)
        db.commit()
        db.refresh(call)

        # 2. Build dynamic variables — injected into the agent's prompt at runtime
        dynamic_vars: Dict[str, str] = {}
        if request.lead_name:
            dynamic_vars["customer_name"] = request.lead_name

        # 3. Build metadata — stored on call object in Retell (retrievable later)
        metadata = request.metadata or {}
        metadata["internal_call_id"] = call.id
        if request.lead_id:
            metadata["lead_id"] = request.lead_id

        # 4. Call Retell API
        try:
            service = get_retell_service()
            retell_call = service.initiate_call(
                to_number=request.to_number,
                agent_id=request.agent_id,
                from_number=request.from_number,
                metadata=metadata,
                dynamic_variables=dynamic_vars if dynamic_vars else None,
            )
        except RetellConfigError as e:
            db.delete(call)
            db.commit()
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            call.status = "failed"
            db.commit()
            logger.error("Retell call initiation failed: %s", e)
            raise HTTPException(status_code=502, detail=f"Retell API error: {str(e)}")

        # 5. Update DB record with Retell call ID
        call.retell_call_id = retell_call.get("call_id")
        call.status = retell_call.get("call_status", "registered")
        db.commit()

        logger.info(
            "Call created | internal_id=%s | retell_call_id=%s",
            call.id, call.retell_call_id,
        )

        return {
            "success": True,
            "message": "Call initiated via Retell AI. Conversation is fully managed by Retell.",
            "internal_call_id": call.id,
            "retell_call_id": call.retell_call_id,
            "status": call.status,
            "to_number": request.to_number,
            "lead_name": request.lead_name,
            "note": "Transcript and summary will be saved automatically when the call ends via /webhook/retell",
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error in initiate_retell_call: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ------------------------------------------------------------------ #
#   POST /api/retell/web-call — browser-based test                    #
# ------------------------------------------------------------------ #

@router.post("/api/retell/web-call", summary="Create a Web Call for testing (Free, no phone needed)")
async def create_retell_web_call(request: WebCallRequest):
    """
    Creates a 'Web Call' session. 
    Use this to test your agent directly in the browser without needing a phone number.
    Returns an access_token and a Retell-hosted link to talk to the agent.
    """
    db = SessionLocal()
    try:
        service = get_retell_service()
        
        # 1. Prepare dynamic variables
        dynamic_vars = {"customer_name": request.lead_name} if request.lead_name else None
        
        # 2. Call Retell
        web_call = service.create_web_call(
            agent_id=request.agent_id,
            metadata=request.metadata,
            dynamic_variables=dynamic_vars
        )
        
        # 3. Create a DB record to track the web call
        call_id = web_call.get("call_id")
        call = Call(
            retell_call_id=call_id,
            lead_name=request.lead_name or "Web User",
            lead_phone="WEB_CALL",
            status="ongoing"
        )
        db.add(call)
        db.commit()

        return {
            "success": True,
            "call_id": call_id,
            "access_token": web_call.get("access_token"),
            "test_url": f"https://dashboard.retellai.com/test-agent/{web_call.get('agent_id')}",
            "note": "You can use the access_token with Retell's Frontend SDK, or just use the dashboard 'Test Agent' button."
        }
    except Exception as e:
        logger.error("Web call creation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ------------------------------------------------------------------ #
#   POST /webhook/retell — Retell event callbacks                     #
# ------------------------------------------------------------------ #

@router.post("/webhook/retell", summary="Retell AI webhook — receives call events", status_code=204)
async def retell_webhook(request: Request):
    """
    Retell POSTs events here as the call progresses.

    Events handled:
      call_started   → update status to 'ongoing'
      call_ended     → save transcript, duration, update status
      call_analyzed  → save call_summary, recording_url

    Set this URL in the Retell Dashboard → Settings → Webhooks:
      https://<your-ngrok-url>/webhook/retell
    """
    # 1. Read raw body (needed for signature verification)
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")

    # 2. Verify Retell signature (security — only accept genuine Retell events)
    api_key = os.getenv("RETELL_API_KEY", "")
    signature = request.headers.get("x-retell-signature", "")

    if api_key and signature:
        try:
            is_valid = Retell.verify(body_str, api_key, signature)
            if not is_valid:
                logger.warning("Invalid Retell webhook signature — rejected")
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Retell signature verification error: %s", e)
            # Don't hard-fail during development if verify() itself errors
    else:
        logger.debug("Skipping signature verification (API key or signature missing)")

    # 3. Parse payload
    try:
        data = json.loads(body_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event = data.get("event", "unknown")
    call_data = data.get("call", {})
    retell_call_id = call_data.get("call_id")

    logger.info("Retell webhook | event=%s | retell_call_id=%s", event, retell_call_id)

    if not retell_call_id:
        logger.warning("Webhook missing call_id — ignoring")
        return Response(status_code=204)

    # 4. Look up call in DB by retell_call_id
    db = SessionLocal()
    try:
        call = db.query(Call).filter(Call.retell_call_id == retell_call_id).first()

        if not call:
            # Could be a call initiated outside this server; log and ignore
            logger.info("No DB record for retell_call_id=%s — skipping", retell_call_id)
            return Response(status_code=204)

        # 5. Handle each event type
        if event == "call_started":
            call.status = "ongoing"
            logger.info("Call started: %s", retell_call_id)

        elif event == "call_ended":
            call.status = call_data.get("call_status", "ended")
            call.transcript = call_data.get("transcript")
            call.duration_ms = call_data.get("duration_ms")
            logger.info(
                "Call ended: %s | duration=%sms | transcript_len=%s",
                retell_call_id,
                call.duration_ms,
                len(call.transcript or ""),
            )

        elif event == "call_analyzed":
            # call_analysis is a sub-object in call_data
            analysis = call_data.get("call_analysis") or {}
            call.call_summary = analysis.get("call_summary")
            call.recording_url = call_data.get("recording_url")
            # Also save transcript if not already saved (in case call_ended was missed)
            if call_data.get("transcript") and not call.transcript:
                call.transcript = call_data.get("transcript")
            logger.info(
                "Call analyzed: %s | summary_len=%s | recording=%s",
                retell_call_id,
                len(call.call_summary or ""),
                bool(call.recording_url),
            )

        else:
            logger.debug("Unhandled Retell event: %s", event)

        db.commit()

    finally:
        db.close()

    # Retell expects HTTP 204 (no content) to acknowledge receipt
    return Response(status_code=204)


# ------------------------------------------------------------------ #
#   GET /api/retell/calls — list calls                                #
# ------------------------------------------------------------------ #

@router.get("/api/retell/calls", summary="List all Retell AI calls")
async def list_retell_calls(limit: int = 50):
    """Returns all calls initiated via Retell, newest first."""
    db = SessionLocal()
    try:
        calls = (
            db.query(Call)
            .filter(Call.retell_call_id.isnot(None))
            .order_by(Call.created_at.desc())
            .limit(limit)
            .all()
        )
        return {
            "total": len(calls),
            "calls": [
                {
                    "id": c.id,
                    "retell_call_id": c.retell_call_id,
                    "lead_name": c.lead_name,
                    "lead_phone": c.lead_phone,
                    "status": c.status,
                    "duration_ms": c.duration_ms,
                    "has_transcript": bool(c.transcript),
                    "has_summary": bool(c.call_summary),
                    "recording_url": c.recording_url,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in calls
            ],
        }
    finally:
        db.close()


# ------------------------------------------------------------------ #
#   GET /api/retell/calls/{id} — single call                         #
# ------------------------------------------------------------------ #

@router.get("/api/retell/calls/{call_id}", summary="Get a Retell AI call with full transcript")
async def get_retell_call(call_id: str):
    """
    Retrieve a single call record by internal DB ID.
    Returns transcript, summary, and recording URL if available.
    """
    db = SessionLocal()
    try:
        # Support lookup by both internal DB id and retell_call_id
        call = (
            db.query(Call).filter(Call.id == call_id).first()
            or db.query(Call).filter(Call.retell_call_id == call_id).first()
        )
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")

        return {
            "id": call.id,
            "retell_call_id": call.retell_call_id,
            "lead_id": call.lead_id,
            "lead_name": call.lead_name,
            "lead_phone": call.lead_phone,
            "status": call.status,
            "duration_ms": call.duration_ms,
            "transcript": call.transcript,
            "call_summary": call.call_summary,
            "recording_url": call.recording_url,
            "created_at": call.created_at.isoformat() if call.created_at else None,
        }
    finally:
        db.close()


# ------------------------------------------------------------------ #
#   Phone Number Management (VoBiz / custom SIP trunk)               #
# ------------------------------------------------------------------ #


@router.post(
    "/api/retell/phone-number/import",
    summary="Import a VoBiz phone number into Retell (bind to SIP trunk)",
)
async def import_phone_number(request: ImportPhoneNumberRequest):
    """
    Connects your VoBiz phone number to Retell AI via SIP trunking.

    **Before calling this endpoint, complete these steps in VoBiz:**
    1. Create a SIP Trunk in VoBiz → note the **Trunk ID** (your termination URI will be `<trunkId>.sip.vobiz.ai`)
    2. Add SIP credentials (username + password) under the trunk's **Credentials** section
    3. Under **Origination URIs**, add: `sip:sip.retellai.com` — this routes inbound calls to Retell
    4. Assign your phone number to this trunk

    Once the number is imported, use it as `from_number` when calling `POST /api/retell/call`.
    """
    try:
        service = get_retell_service()
        result = service.import_phone_number(
            phone_number=request.phone_number,
            termination_uri=request.termination_uri,
            sip_trunk_auth_username=request.sip_trunk_auth_username,
            sip_trunk_auth_password=request.sip_trunk_auth_password,
            inbound_agent_id=request.inbound_agent_id,
            outbound_agent_id=request.outbound_agent_id,
            nickname=request.nickname,
            transport=request.transport,
        )
        return {
            "success": True,
            "message": f"Phone number {request.phone_number} successfully imported into Retell.",
            "phone_number": result.get("phone_number"),
            "phone_number_type": result.get("phone_number_type"),
            "inbound_agent_id": result.get("inbound_agent_id"),
            "outbound_agent_id": result.get("outbound_agent_id"),
            "next_step": f"Use '{request.phone_number}' as from_number in POST /api/retell/call",
        }
    except RetellConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Phone number import failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Retell API error: {str(e)}")


@router.get(
    "/api/retell/phone-numbers",
    summary="List all phone numbers registered in Retell",
)
async def list_phone_numbers():
    """Returns all phone numbers connected to your Retell account with their bound agents."""
    try:
        service = get_retell_service()
        numbers = service.list_phone_numbers()
        return {
            "success": True,
            "count": len(numbers),
            "phone_numbers": [
                {
                    "phone_number": n.get("phone_number"),
                    "nickname": n.get("nickname"),
                    "phone_number_type": n.get("phone_number_type"),
                    "inbound_agent_id": n.get("inbound_agent_id"),
                    "outbound_agent_id": n.get("outbound_agent_id"),
                }
                for n in numbers
            ],
        }
    except Exception as e:
        logger.error("Failed to list phone numbers: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@router.delete(
    "/api/retell/phone-number/{phone_number:path}",
    summary="Remove a phone number from Retell (does not delete from VoBiz)",
    status_code=200,
)
async def delete_phone_number(phone_number: str):
    """
    Disconnects a phone number from your Retell account.
    The number will remain active in VoBiz — this only removes it from Retell.

    Pass the number URL-encoded, e.g. `/api/retell/phone-number/%2B91XXXXXXXXXX`
    """
    try:
        service = get_retell_service()
        service.delete_phone_number(phone_number)
        return {
            "success": True,
            "message": f"{phone_number} has been removed from Retell.",
            "note": "The number is still active in VoBiz. Re-import it anytime.",
        }
    except Exception as e:
        logger.error("Phone number deletion failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
