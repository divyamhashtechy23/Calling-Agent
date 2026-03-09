from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


# ===============================
# Call start response (SYNC)
# ===============================
class CallStartResponse(BaseModel):
    callId: str
    status: str

    orgId: str
    sequenceId: str
    leadId: str

    timestamp: datetime


# ===============================
# Call result (ASYNC / WEBHOOK)
# ===============================
class CallResult(BaseModel):
    execution_id: str
    agent_id: Optional[str] = None
    status: str

    duration_seconds: Optional[float] = None
    total_cost_cents: Optional[float] = None

    transcript: Optional[str] = None
    recording_url: Optional[str] = None

    answered_by_voice_mail: Optional[bool] = None

    raw: Dict[str, Any]  # full Bolna payload for audit/debug
