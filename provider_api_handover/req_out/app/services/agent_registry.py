from fastapi import HTTPException
from app.config import settings

LANGUAGE_AGENT_MAP = {
    "en": settings.BOLNA_AGENT_EN,
    "hi": settings.BOLNA_AGENT_HI,
    "gu": settings.BOLNA_AGENT_GU,
}

def get_agent_id(language: str) -> str:
    agent_id = LANGUAGE_AGENT_MAP.get(language.lower())
    if not agent_id:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: {language}"
        )
    return agent_id
