"""
Pydantic Schemas — request/response validation for the API.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime


class InitiateCallRequest(BaseModel):
    """Payload to start an outbound call with organization and lead context."""
    orgId: str = Field(..., description="Organization ID")
    userId: str = Field(..., description="User ID who initiated the call")
    sequenceId: str = Field(..., description="Sequence or Campaign ID")
    leadId: str = Field(..., description="Internal Lead ID")
    leadName: str = Field(..., description="Lead Name")
    leadPhone: str = Field(..., description="Lead Phone Number in E.164 format")
    leadCompany: Optional[str] = Field(None, description="Company Name")
    language: str = Field("en", description="Call language code")
    callPurpose: str = Field(..., description="Main goal of the call")
    callingScript: str = Field(..., description="Guidelines for the AI to follow")
    callerName: str = Field(..., description="The name the AI will use")
    orgName: str = Field(..., description="The organization the AI represents")

    agent_id: Optional[str] = None
    from_number: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "orgId": "org1",
                "userId": "user1",
                "sequenceId": "seq1",
                "leadId": "lead1",
                "leadName": "Shivi",
                "leadPhone": "+916261652154",
                "leadCompany": "Hashtechy",
                "language": "en",
                "callPurpose": "Quick introduction to our AI services",
                "callingScript": (
                    "- Introduce company briefly\n"
                    "- Ask if they are exploring AI initiatives\n"
                    "- If interested, confirm specialist follow-up\n"
                    "- If not interested, thank and close"
                ),
                "callerName": "Salesy",
                "orgName": "Hashtechy",
            }
        }


class ConnectSipTrunkRequest(BaseModel):
    """Payload to connect an external SIP trunk phone number to Bolna (BYOT)."""
    name: str = Field(
        ...,
        description="Friendly label for this trunk",
        examples=["My VoBiz Trunk"],
    )
    provider: str = Field(
        ...,
        description="Telephony provider name (e.g. 'vobiz', 'twilio', 'plivo')",
        examples=["vobiz"],
    )
    phone_number: str = Field(
        ...,
        description="Phone number in E.164 format",
        examples=["+919XXXXXXXX"],
    )
    gateway_address: str = Field(
        ...,
        description="SIP trunk gateway address",
        examples=["8bb6434a.sip.vobiz.ai"],
    )
    auth_type: str = Field(
        "userpass",
        description="Authentication method: 'userpass' or 'ip-based'",
    )
    auth_username: Optional[str] = Field(
        None,
        description="SIP auth username (required for 'userpass' auth)",
    )
    auth_password: Optional[str] = Field(
        None,
        description="SIP auth password (required for 'userpass' auth)",
    )


class BuyPhoneNumberRequest(BaseModel):
    """Payload to buy a phone number from Bolna."""
    country: str = Field(
        "IN",
        description="Two-letter country code (e.g. IN, US, GB)",
    )
    phone_number: Optional[str] = Field(
        None,
        description="Optional: specific number to purchase",
    )


class ConnectProviderRequest(BaseModel):
    """
    Payload to connect a business's telephony provider to Bolna.
    Provider credentials are passed as flexible key-value pairs since
    different providers require different fields.
    """
    provider: str = Field(
        ...,
        description=(
            "Telephony provider name. "
            "Supported: 'vobiz', 'twilio', 'plivo', 'exotel'"
        ),
        examples=["vobiz", "twilio", "plivo", "exotel"],
    )

    credentials: Dict[str, str] = Field(
        ...,
        description=(
            "Provider credentials as key-value pairs. "
            "Use GET /api/bolna/providers/fields/{provider} to see required fields."
        ),
        examples=[{
            "api_key": "your_api_key",
            "api_secret": "your_api_secret",
            "phone_number": "+917971543244",
        }],
    )

    class Config:
        json_schema_extra = {
            "example": {
                "provider": "vobiz",
                "credentials": {
                    "api_key": "your_vobiz_api_key",
                    "api_secret": "your_vobiz_api_secret",
                    "phone_number": "+917971543244",
                },
            }
        }


# ── AiCallTracking Response ─────────────────────────────────────────── #

class AiCallTrackingResponse(BaseModel):
    """Single AiCallTracking record returned by the GET API."""
    call_id: Optional[str] = None
    start_status: Optional[str] = None
    org_id: Optional[str] = None
    sequence_id: Optional[str] = None
    lead_id: Optional[str] = None
    start_timestamp: Optional[datetime] = None
    final_status: Optional[str] = None
    event_type: Optional[str] = None
    initiated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    total_cost: Optional[float] = None
    interest_level: Optional[str] = None
    callback_requested: Optional[bool] = None
    callback_time: Optional[str] = None
    stop_sequence: Optional[Union[str, bool]] = None
    notes: Optional[str] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    recording_url: Optional[str] = None
    provider_name: Optional[str] = None
    telephony_provider: Optional[str] = None
    agent_id: Optional[str] = None
    provider_call_id: Optional[str] = None
    hangup_reason: Optional[str] = None
    raw_webhook_json: Optional[str] = None
    webhook_received_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class AiCallTrackingListResponse(BaseModel):
    """Paginated list of AiCallTracking records."""
    total_count: int = Field(..., description="Total number of records matching the query")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Current offset")
    records: List[AiCallTrackingResponse] = Field(..., description="List of call-tracking records")

class CreateBatchRequest(BaseModel):
    agent_id: Optional[str] = None

class ScheduleBatchRequest(BaseModel):
    scheduled_at: str = Field(
        ...,
        description="ISO 8601 datetime e.g. '2024-06-04T22:40:00.000Z'",
        examples=["2024-06-04T22:40:00.000Z"]
    )

# ── Campaign Templates ────────────────────────────────────────── #
class TemplateCreate(BaseModel):
    template_name: str
    industry: str
    language: Optional[str] = "en"
    org_name: str
    caller_name: str
    call_purpose: str
    call_script: str
class TemplateResponse(BaseModel):
    temp_id: int
    user_id: str
    template_name: str
    industry: str
    language: str
    org_name: str
    caller_name: str
    call_purpose: str
    call_script: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True