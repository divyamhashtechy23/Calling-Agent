"""
Provider & SIP Trunk routes — two methods for businesses to connect
their phone numbers to Bolna AI.
"""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import verify_api_key
from app.schemas.provider import ConnectProviderRequest, ConnectSipTrunkRequest
from app.services import provider_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Provider credential endpoints ────────────────────────────────────── #

@router.get("/supported", summary="List supported telephony providers")
async def list_supported_providers():
    """Returns provider names for a frontend dropdown."""
    providers = provider_client.get_supported_providers()
    return {
        "success": True,
        "supported_providers": providers,
        "count": len(providers),
    }


@router.get("/fields/{provider}", summary="Get required fields for a provider")
async def get_provider_fields(provider: str):
    """Returns the credential fields the business must fill in."""
    try:
        fields = provider_client.get_required_fields(provider)
        return {
            "success": True,
            "provider": provider.lower(),
            "required_fields": fields,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/connect", summary="Connect a telephony provider")
async def connect_provider(
    request: ConnectProviderRequest,
    _=Depends(verify_api_key),
):
    """Save a business's provider credentials to Bolna."""
    try:
        result = await provider_client.connect_provider(
            provider=request.provider,
            credentials=request.credentials,
        )
        return {"success": True, "message": f"Provider '{request.provider}' connected.", **result}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except httpx.HTTPStatusError as exc:
        logger.error("Bolna provider connect failed: %s", exc.response.text)
        raise HTTPException(status_code=502, detail=f"Bolna API error: {exc.response.text[:500]}")


@router.get("/", summary="List all connected provider credentials")
async def list_providers(_=Depends(verify_api_key)):
    """Returns stored credentials (values masked by Bolna)."""
    try:
        result = await provider_client.list_providers()
        return {"success": True, "providers": result}
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Bolna API error: {exc.response.text[:500]}")


@router.delete("/disconnect/{provider}", summary="Disconnect a provider")
async def disconnect_provider(
    provider: str,
    _=Depends(verify_api_key),
):
    """Remove ALL credentials for a provider so it can be reconnected."""
    try:
        result = await provider_client.disconnect_provider(provider)
        return {
            "success": True,
            "message": f"Provider '{provider}' disconnected — {result['credentials_deleted']} credentials removed.",
            **result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except httpx.HTTPStatusError as exc:
        logger.error("Provider disconnect failed: %s", exc.response.text)
        raise HTTPException(status_code=502, detail=f"Bolna API error: {exc.response.text[:500]}")


# ── SIP Trunk endpoints ──────────────────────────────────────────────── #

@router.post("/sip-trunks", summary="Create a SIP trunk (BYOT)")
async def create_sip_trunk(
    request: ConnectSipTrunkRequest,
    _=Depends(verify_api_key),
):
    """Connect a business phone number via SIP trunk."""
    if not request.phone_number.startswith("+") or len(request.phone_number) < 10:
        raise HTTPException(status_code=400, detail="Phone number must be in E.164 format")

    try:
        result = await provider_client.create_sip_trunk(
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
            "message": f"SIP trunk created for {request.phone_number}.",
            "trunk_id": result.get("id") or result.get("trunk_id"),
            "phone_number": request.phone_number,
        }
    except httpx.HTTPStatusError as exc:
        logger.error("SIP trunk creation failed: %s", exc.response.text)
        raise HTTPException(status_code=502, detail=f"Bolna API error: {exc.response.text[:500]}")


@router.get("/sip-trunks", summary="List all SIP trunks")
async def list_sip_trunks(_=Depends(verify_api_key)):
    """Returns all SIP trunks connected to the Bolna account."""
    try:
        trunks = await provider_client.list_sip_trunks()
        return {
            "success": True,
            "count": len(trunks) if isinstance(trunks, list) else 0,
            "sip_trunks": trunks,
        }
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Bolna API error: {exc.response.text[:500]}")


@router.patch("/sip-trunks/{trunk_id}", summary="Update a SIP trunk")
async def update_sip_trunk(
    trunk_id: str,
    request: Request,
    _=Depends(verify_api_key),
):
    """Update an existing SIP trunk configuration."""
    try:
        body = await request.json()
        result = await provider_client.update_sip_trunk(trunk_id, body)
        return {"success": True, "trunk": result}
    except httpx.HTTPStatusError as exc:
        logger.error("SIP trunk update failed: %s", exc.response.text)
        raise HTTPException(status_code=502, detail=f"Bolna API error: {exc.response.text[:500]}")
