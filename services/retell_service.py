"""
RetellService — thin wrapper around the retell-sdk Python client.

Responsibilities:
  - Initialize the Retell client from RETELL_API_KEY env var
  - initiate_call()          → create an outbound phone call
  - create_web_call()        → create a browser-based test call
  - import_phone_number()    → connect a VoBiz/custom SIP trunk number
  - list_phone_numbers()     → list all numbers on Retell account
  - delete_phone_number()    → remove a number from Retell
"""

import os
import logging
from typing import Optional, Dict, Any

from retell import Retell

logger = logging.getLogger(__name__)


class RetellConfigError(Exception):
    """Raised when required Retell env vars are missing."""


class RetellService:
    """
    Async-friendly Retell API wrapper.
    Instantiate once and share across requests.
    """

    def __init__(self):
        self.api_key = os.getenv("RETELL_API_KEY", "")
        if not self.api_key:
            raise RetellConfigError(
                "RETELL_API_KEY is not set. Add it to your .env file."
            )
        self.client = Retell(api_key=self.api_key)
        self.default_agent_id = os.getenv("RETELL_AGENT_ID", "")
        self.default_from_number = os.getenv("RETELL_FROM_NUMBER", "")
        logger.info("RetellService initialized (agent_id=%s)", self.default_agent_id)

    def initiate_call(
        self,
        to_number: str,
        agent_id: Optional[str] = None,
        from_number: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        dynamic_variables: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create an outbound phone call via Retell.

        Args:
            to_number:         Destination number in E.164 format (+91XXXXXXXXXX)
            agent_id:          Override agent for this call. Falls back to RETELL_AGENT_ID.
            from_number:       Caller number in E.164 format. Falls back to RETELL_FROM_NUMBER.
            metadata:          Arbitrary dict stored on the call (not used for processing).
            dynamic_variables: Key-value pairs injected into the agent's prompt at runtime.

        Returns:
            The Retell call object as a dict.

        Raises:
            RetellConfigError: If agent_id or from_number are not provided and not in env.
            Exception:         If the Retell API returns an error.
        """
        resolved_agent_id = agent_id or self.default_agent_id
        resolved_from_number = from_number or self.default_from_number

        if not resolved_agent_id:
            raise RetellConfigError(
                "No agent_id provided and RETELL_AGENT_ID is not set in .env."
            )
        if not resolved_from_number:
            raise RetellConfigError(
                "No from_number provided and RETELL_FROM_NUMBER is not set in .env."
            )

        kwargs: Dict[str, Any] = {
            "from_number": resolved_from_number,
            "to_number": to_number,
            "override_agent_id": resolved_agent_id,
        }
        if metadata:
            kwargs["metadata"] = metadata
        if dynamic_variables:
            kwargs["retell_llm_dynamic_variables"] = dynamic_variables

        logger.info(
            "Initiating Retell call | to=%s | agent=%s", to_number, resolved_agent_id
        )
        response = self.client.call.create_phone_call(**kwargs)

        # retell-sdk returns a Pydantic-like object — convert to dict
        result = response.model_dump() if hasattr(response, "model_dump") else dict(response)
        logger.info(
            "Retell call created | call_id=%s | status=%s",
            result.get("call_id"),
            result.get("call_status"),
        )
        return result

    def create_web_call(
        self,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        dynamic_variables: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a Web Call (browser-based conversation).
        Returns a dictionary containing the 'access_token' needed for frontend.
        """
        resolved_agent_id = agent_id or self.default_agent_id
        if not resolved_agent_id:
            raise RetellConfigError("RETELL_AGENT_ID not set.")

        kwargs = {"agent_id": resolved_agent_id}
        if metadata:
            kwargs["metadata"] = metadata
        if dynamic_variables:
            kwargs["retell_llm_dynamic_variables"] = dynamic_variables

        response = self.client.call.create_web_call(**kwargs)
        return response.model_dump() if hasattr(response, "model_dump") else dict(response)

    # ------------------------------------------------------------------ #
    #  Phone Number Management                                             #
    # ------------------------------------------------------------------ #

    def import_phone_number(
        self,
        phone_number: str,
        termination_uri: str,
        sip_trunk_auth_username: Optional[str] = None,
        sip_trunk_auth_password: Optional[str] = None,
        inbound_agent_id: Optional[str] = None,
        outbound_agent_id: Optional[str] = None,
        nickname: Optional[str] = None,
        transport: str = "TCP",
    ) -> Dict[str, Any]:
        """
        Import a VoBiz (or any custom SIP trunk) phone number into Retell.

        Args:
            phone_number:             E.164 format, e.g. +91XXXXXXXXXX
            termination_uri:          Your VoBiz SIP trunk URI, e.g. trunkId.sip.vobiz.ai
            sip_trunk_auth_username:  SIP credentials (optional but recommended)
            sip_trunk_auth_password:  SIP credentials (optional but recommended)
            inbound_agent_id:         Agent to handle inbound calls. Defaults to RETELL_AGENT_ID.
            outbound_agent_id:        Agent to handle outbound calls. Defaults to RETELL_AGENT_ID.
            nickname:                 Friendly label shown in the Retell dashboard.
            transport:                SIP transport: "TCP" (default), "UDP", or "TLS".
        """
        resolved_inbound_agent  = inbound_agent_id  or self.default_agent_id or None
        resolved_outbound_agent = outbound_agent_id or self.default_agent_id or None

        kwargs: Dict[str, Any] = {
            "phone_number":    phone_number,
            "termination_uri": termination_uri,
            "transport":       transport,
        }
        if sip_trunk_auth_username:
            kwargs["sip_trunk_auth_username"] = sip_trunk_auth_username
        if sip_trunk_auth_password:
            kwargs["sip_trunk_auth_password"] = sip_trunk_auth_password
        if resolved_inbound_agent:
            kwargs["inbound_agent_id"] = resolved_inbound_agent
        if resolved_outbound_agent:
            kwargs["outbound_agent_id"] = resolved_outbound_agent
        if nickname:
            kwargs["nickname"] = nickname

        logger.info("Importing phone number %s into Retell (trunk=%s)", phone_number, termination_uri)
        response = self.client.phone_number.import_(**kwargs)
        return response.model_dump() if hasattr(response, "model_dump") else dict(response)

    def list_phone_numbers(self) -> list:
        """Return all phone numbers registered on this Retell account."""
        response = self.client.phone_number.list()
        return [
            (r.model_dump() if hasattr(r, "model_dump") else dict(r))
            for r in response
        ]

    def delete_phone_number(self, phone_number: str) -> None:
        """Remove a phone number from Retell (does NOT delete it from VoBiz/Twilio)."""
        logger.info("Deleting phone number %s from Retell", phone_number)
        self.client.phone_number.delete(phone_number)

