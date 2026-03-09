"""
Telephony provider management — connect/disconnect business credentials
and SIP trunks to Bolna AI.
"""

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ── Provider credential registry ────────────────────────────────────── #
# Maps friendly field names to Bolna's internal key names per provider.
# Adding a new provider = adding one dictionary entry here.

PROVIDER_CREDENTIALS: dict[str, dict[str, str]] = {
    "vobiz": {
        "api_key":      "VOBIZ_API_KEY",
        "api_secret":   "VOBIZ_API_SECRET",
        "phone_number": "VOBIZ_PHONE_NUMBER",
    },
    "twilio": {
        "account_sid":  "TWILIO_ACCOUNT_SID",
        "auth_token":   "TWILIO_AUTH_TOKEN",
        "phone_number": "TWILIO_PHONE_NUMBER",
    },
    "plivo": {
        "auth_id":      "PLIVO_AUTH_ID",
        "auth_token":   "PLIVO_AUTH_TOKEN",
        "phone_number": "PLIVO_PHONE_NUMBER",
    },
    "exotel": {
        "api_key":          "EXOTEL_API_KEY",
        "api_token":        "EXOTEL_API_TOKEN",
        "account_sid":      "EXOTEL_ACCOUNT_SID",
        "domain":           "EXOTEL_DOMAIN",
        "phone_number":     "EXOTEL_PHONE_NUMBER",
        "outbound_app_id":  "EXOTEL_OUTBOUND_APP_ID",
        "inbound_app_id":   "EXOTEL_INBOUND_APP_ID",
    },
}

BOLNA_HEADERS = {
    "Authorization": f"Bearer {settings.BOLNA_API_KEY}",
    "Content-Type": "application/json",
}


# ── Helper functions ─────────────────────────────────────────────────── #

def get_supported_providers() -> list[str]:
    return list(PROVIDER_CREDENTIALS.keys())


def get_required_fields(provider: str) -> list[str]:
    cred_map = PROVIDER_CREDENTIALS.get(provider.lower())
    if not cred_map:
        raise ValueError(
            f"Unsupported provider '{provider}'. "
            f"Supported: {get_supported_providers()}"
        )
    return list(cred_map.keys())


# ── Provider credential endpoints ────────────────────────────────────── #

async def connect_provider(provider: str, credentials: dict[str, str]) -> dict[str, Any]:
    """Validate and save each credential to Bolna's /providers vault."""
    provider_lower = provider.lower()
    cred_map = PROVIDER_CREDENTIALS.get(provider_lower)
    if not cred_map:
        raise ValueError(
            f"Unsupported provider '{provider}'. "
            f"Supported: {get_supported_providers()}"
        )

    # Check all required fields are present
    missing = set(cred_map.keys()) - set(credentials.keys())
    if missing:
        raise ValueError(
            f"Missing required fields for {provider}: {sorted(missing)}. "
            f"Required: {sorted(cred_map.keys())}"
        )

    results = []
    async with httpx.AsyncClient(timeout=30) as client:
        for friendly_name, bolna_key in cred_map.items():
            value = credentials[friendly_name]

            logger.info("Setting credential | provider=%s | key=%s", provider, bolna_key)

            response = await client.post(
                f"{settings.BOLNA_BASE_URL}/providers",
                headers=BOLNA_HEADERS,
                json={"provider_name": bolna_key, "provider_value": value},
            )

            # Already exists — treat as success
            if response.status_code == 409:
                logger.info("Credential %s already exists, skipping", bolna_key)
                results.append({"field": friendly_name, "bolna_key": bolna_key, "status": "already_exists"})
                continue

            response.raise_for_status()
            results.append({"field": friendly_name, "bolna_key": bolna_key, "status": "saved"})

    return {"provider": provider, "credentials_saved": len(results), "details": results}


async def disconnect_provider(provider: str) -> dict[str, Any]:
    """Remove ALL stored credentials for a given provider from Bolna."""
    provider_lower = provider.lower()
    cred_map = PROVIDER_CREDENTIALS.get(provider_lower)
    if not cred_map:
        raise ValueError(
            f"Unsupported provider '{provider}'. "
            f"Supported: {get_supported_providers()}"
        )

    bolna_keys = set(cred_map.values())
    deleted = []

    async with httpx.AsyncClient(timeout=30) as client:
        # Fetch all stored credentials
        resp = await client.get(
            f"{settings.BOLNA_BASE_URL}/providers",
            headers=BOLNA_HEADERS,
        )
        resp.raise_for_status()
        all_creds = resp.json().get("providers", [])

        # Delete each credential that belongs to this provider
        for cred in all_creds:
            if cred.get("provider_name") in bolna_keys:
                del_resp = await client.delete(
                    f"{settings.BOLNA_BASE_URL}/providers/{cred['provider_id']}",
                    headers=BOLNA_HEADERS,
                )
                logger.info(
                    "Deleted %s (%s) | status=%s",
                    cred["provider_name"], cred["provider_id"], del_resp.status_code,
                )
                deleted.append({
                    "bolna_key": cred["provider_name"],
                    "provider_id": cred["provider_id"],
                    "status": "deleted",
                })

    return {"provider": provider, "credentials_deleted": len(deleted), "details": deleted}


async def list_providers() -> dict[str, Any]:
    """List all provider credentials stored in Bolna (values are masked)."""
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{settings.BOLNA_BASE_URL}/providers",
            headers=BOLNA_HEADERS,
        )
        resp.raise_for_status()
        return resp.json()


# ── SIP trunk endpoints ──────────────────────────────────────────────── #

async def create_sip_trunk(
    name: str,
    provider: str,
    phone_number: str,
    gateway_address: str,
    auth_type: str = "userpass",
    auth_username: str | None = None,
    auth_password: str | None = None,
) -> dict[str, Any]:
    """Create a new SIP trunk in Bolna for BYOT phone numbers."""
    payload: dict[str, Any] = {
        "name": name,
        "provider": provider,
        "phone_number": phone_number,
        "termination_uri": gateway_address,
    }
    if auth_type == "userpass" and auth_username:
        payload["auth_username"] = auth_username
        payload["auth_password"] = auth_password

    logger.info("Creating SIP trunk | number=%s | gateway=%s", phone_number, gateway_address)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.BOLNA_BASE_URL}/sip-trunks/trunks",
            headers=BOLNA_HEADERS,
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


async def list_sip_trunks() -> list[dict]:
    """List all SIP trunks on the Bolna account."""
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{settings.BOLNA_BASE_URL}/sip-trunks/trunks",
            headers=BOLNA_HEADERS,
        )
        resp.raise_for_status()
        return resp.json()


async def update_sip_trunk(trunk_id: str, updates: dict) -> dict[str, Any]:
    """Update an existing SIP trunk configuration."""
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.patch(
            f"{settings.BOLNA_BASE_URL}/sip-trunks/trunks/{trunk_id}",
            headers=BOLNA_HEADERS,
            json=updates,
        )
        resp.raise_for_status()
        return resp.json()
