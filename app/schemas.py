from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class InitiateCallRequest(BaseModel):
    """Payload to start a Retell outbound call."""
    to_number: str = Field(..., description="Destination in E.164 format, e.g. +91XXXXXXXXXX")
    agent_id: Optional[str] = Field(None, description="Override agent ID (defaults to RETELL_AGENT_ID env var)")
    from_number: Optional[str] = Field(None, description="Caller number (defaults to RETELL_FROM_NUMBER env var)")
    lead_name: Optional[str] = Field(None, description="Customer name — injected into agent prompt as dynamic variable")
    lead_id: Optional[str] = Field(None, description="Your internal lead identifier, stored on the call record")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Arbitrary metadata stored with the call (not used for processing)")

    class Config:
        json_schema_extra = {
            "example": {
                "to_number": "+919XXXXXXXX",
                "lead_name": "John Doe",
                "lead_id": "lead_001",
            }
        }

class WebCallRequest(BaseModel):
    """Payload to create a browser-based web call session."""
    agent_id: Optional[str] = None
    lead_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ImportPhoneNumberRequest(BaseModel):
    """Payload to import a VoBiz/custom SIP trunk phone number into Retell."""
    phone_number: str = Field(
        ...,
        description="Your phone number in E.164 format, e.g. +91XXXXXXXXXX",
        example="+919XXXXXXXX"
    )
    termination_uri: str = Field(
        ...,
        description="VoBiz SIP trunk termination URI, e.g. your-trunk-id.sip.vobiz.ai",
        example="your-trunk-id.sip.vobiz.ai"
    )
    sip_trunk_auth_username: Optional[str] = Field(
        None,
        description="SIP credential username from VoBiz trunk settings"
    )
    sip_trunk_auth_password: Optional[str] = Field(
        None,
        description="SIP credential password from VoBiz trunk settings"
    )
    inbound_agent_id: Optional[str] = Field(
        None,
        description="Agent to use for inbound calls. Defaults to RETELL_AGENT_ID from .env"
    )
    outbound_agent_id: Optional[str] = Field(
        None,
        description="Agent to use for outbound calls. Defaults to RETELL_AGENT_ID from .env"
    )
    nickname: Optional[str] = Field(
        None,
        description="Friendly label for this number in the Retell dashboard",
        example="My VoBiz Line"
    )
    transport: str = Field(
        "TCP",
        description="SIP transport protocol: TCP (recommended), UDP, or TLS"
    )