from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class InitiateCallRequest(BaseModel):
    """Payload to start a Retell outbound call with full organization and lead context."""
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
    
    # Optional Retell overrides
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
                "callingScript": "- Introduce company briefly\n- Ask if they are exploring AI initiatives\n- If interested, confirm specialist follow-up\n- If not interested, thank and close",
                "callerName": "Salesy",
                "orgName": "Hashtechy"
            }
        }

    
class WebCallRequest(BaseModel):
    """Payload to create a browser-based web call session."""
    agent_id: Optional[str] = None
    lead_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ConnectPhoneNumberRequest(BaseModel):
    """Payload to connect a phone number to Retell."""
    phone_number: str = Field(
        ...,
        description="Your phone number in E.164 format, e.g. +91XXXXXXXXXX",
        example="+919XXXXXXXX"
    )
    
    termination_uri: str = Field(
        ...,
        description="SIP trunk termination URI, e.g. your-trunk-id.sip",
        example="your-trunk-id.sip"
    )
    
    sip_trunk_username: Optional[str] = Field(
        None,
        description="SIP credential username from your respective SIP trunk settings" 
    )
    
    sip_trunk_password: Optional[str] = Field(
        None,
        description="SIP credential password from your respective SIP trunk settings"
    )
    
    nickname: Optional[str] = Field(
        None,
        description="Friendly label for this number in the Retell dashboard",
        example="My Line"
    )
    
    transport: str = Field(
        "TCP",
        description="SIP transport protocol: TCP (recommended), UDP, or TLS"
    )