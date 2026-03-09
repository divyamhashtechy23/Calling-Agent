# app/services/notifier.py

import httpx
import logging
from app.config import settings

logger = logging.getLogger(__name__)


async def send_to_crm(payload: dict):
    if not payload:
        return

    if not settings.DOTNET_WEBHOOK_URL:
        logger.warning("DOTNET_WEBHOOK_URL not set, skipping CRM notify")
        return

    if not settings.DOTNET_WEBHOOK_URL.startswith(("http://", "https://")):
        logger.error("Invalid DOTNET_WEBHOOK_URL, skipping CRM notify")
        return

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    settings.DOTNET_WEBHOOK_URL,
                    json=payload,
                    headers={
                        "X-Source": "ai-calling-service",
                        "X-Event-Type": payload.get("eventType", "unknown")
                    }
                )

                if response.status_code < 300:
                    return

                logger.error(
                    f"CRM notify failed (status={response.status_code}) "
                    f"attempt={attempt + 1}"
                )

        except Exception as e:
            logger.error(f"CRM notify exception attempt={attempt + 1}: {e}")
