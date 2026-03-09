from pydantic import BaseModel, Field
from typing import Dict, Optional


class ConnectProviderRequest(BaseModel):
    """Credentials payload for linking a telephony provider to Bolna."""
    provider: str = Field(..., description="Provider name: vobiz | twilio | plivo | exotel")
    credentials: Dict[str, str] = Field(..., description="Key-value credential pairs")


class ConnectSipTrunkRequest(BaseModel):
    """SIP trunk config for BYOT (Bring Your Own Telephony)."""
    name: str = Field(..., description="Friendly trunk name")
    provider: str = Field(..., description="SIP provider name, e.g. vobiz")
    phone_number: str = Field(..., description="E.164 DID number, e.g. +917971543244")
    gateway_address: str = Field(..., description="SIP gateway URI, e.g. 1e4ed098.sip.vobiz.ai")
    auth_type: str = Field("userpass", description="Auth method: userpass | ip")
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
