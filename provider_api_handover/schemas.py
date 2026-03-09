"""
Pydantic Schemas — request/response validation for the API.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


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