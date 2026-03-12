"""
BolnaService — HTTP wrapper around the Bolna AI REST API.

Uses httpx for direct REST API calls (Bolna has no Python SDK).

Endpoints:
    - initiate_call()        → POST /call
    - get_execution()        → GET  /executions/{id}
    - list_agents()          → GET  /agent/all
    - buy_phone_number()     → POST /phone-numbers/buy
    - search_phone_numbers() → GET  /phone-numbers/search
    - list_phone_numbers()   → GET  /phone-numbers/all
    - delete_phone_number()  → DEL  /phone-numbers/{id}
    - create_sip_trunk()     → POST /sip-trunks/trunks
    - list_sip_trunks()      → GET  /sip-trunks/trunks
    - update_sip_trunk()     → PATCH /sip-trunks/trunks/{id}
    - connect_provider()     → POST /providers  (multiple calls)
    - list_providers()       → GET  /providers
    - delete_provider()      → DEL  /providers/{id}
    - create_batch()         → POST /batches
    - schedule_batch()       → POST /batches/{id}/schedule
    - get_batch()            → GET  /batches/{id}
    - list_batches()         → GET  /batches
    - stop_batch()           → POST /batches/{id}/stop
    - get_batch_executions() → GET  /batches/{id}/executions
"""
import io 
import csv
import os
import logging
from typing import Optional, Dict, Any, List

import httpx

logger = logging.getLogger(__name__)

BOLNA_BASE_URL = "https://api.bolna.ai"


class BolnaConfigError(Exception):
    """Raised when required Bolna env vars are missing."""


class BolnaService:
    """Bolna AI API wrapper. Instantiate once and share across requests."""

    def __init__(self):
        self.api_key = os.getenv("BOLNA_API_KEY", "")
        if not self.api_key:
            raise BolnaConfigError(
                "BOLNA_API_KEY is not set. Add it to your .env file. "
                "Get it from https://platform.bolna.ai/developers"
            )

        self.client = httpx.Client(
            base_url=BOLNA_BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

        self.default_agent_id = os.getenv("BOLNA_AGENT_ID", "")
        self.default_from_number = os.getenv("BOLNA_FROM_NUMBER", "")
        logger.info("BolnaService initialized (agent_id=%s)", self.default_agent_id)

    def _check_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Parse response JSON, raise on non-2xx status."""
        if response.status_code >= 400:
            try:
                error_detail = response.json()
            except Exception:
                error_detail = response.text
            logger.error(
                "Bolna API error | status=%s | detail=%s",
                response.status_code,
                error_detail,
            )
            raise Exception(
                f"Bolna API error ({response.status_code}): {error_detail}"
            )
        return response.json()

    # ── Calling ──────────────────────────────────────────────────────── #

    def initiate_call(
        self,
        to_number: str,
        agent_id: Optional[str] = None,
        from_number: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_data: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create an outbound phone call via Bolna.

        Args:
            to_number:   Destination in E.164 format
            agent_id:    Override default agent
            from_number: Override default caller number
            metadata:    Extra context merged into user_data
            user_data:   Key-value pairs injected into agent context
        """
        resolved_agent_id = agent_id or self.default_agent_id
        resolved_from_number = from_number or self.default_from_number

        if not resolved_agent_id:
            raise BolnaConfigError(
                "No agent_id provided and BOLNA_AGENT_ID is not set in .env."
            )

        payload: Dict[str, Any] = {
            "agent_id": resolved_agent_id,
            "recipient_phone_number": to_number,
        }

        if resolved_from_number:
            payload["from_phone_number"] = resolved_from_number

        combined_user_data = {}
        if user_data:
            combined_user_data.update(user_data)
        if metadata:
            combined_user_data.update(metadata)
        if combined_user_data:
            payload["user_data"] = combined_user_data

        logger.info(
            "Initiating Bolna call | to=%s | agent=%s", to_number, resolved_agent_id
        )

        response = self.client.post("/call", json=payload)
        result = self._check_response(response)

        logger.info(
            "Bolna call created | execution_id=%s | status=%s",
            result.get("execution_id") or result.get("id"),
            result.get("status"),
        )
        return result

    # ── Execution Details ────────────────────────────────────────────── #

    def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """Fetch call details by execution ID (status, transcript, recording)."""
        response = self.client.get(f"/executions/{execution_id}")
        return self._check_response(response)

    # ── Agents ───────────────────────────────────────────────────────── #

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all AI agents in your Bolna account."""
        response = self.client.get("/agent/all")
        return self._check_response(response)

    # ── Phone Number Management ──────────────────────────────────────── #

    def buy_phone_number(
        self,
        country: str = "IN",
        phone_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Buy a virtual phone number from Bolna."""
        payload: Dict[str, Any] = {"country": country}
        if phone_number:
            payload["phone_number"] = phone_number
        response = self.client.post("/phone-numbers/buy", json=payload)
        return self._check_response(response)

    def search_phone_numbers(self, country: str = "IN") -> List[Dict[str, Any]]:
        """Search available phone numbers by country."""
        response = self.client.get("/phone-numbers/search", params={"country": country})
        return self._check_response(response)

    def list_phone_numbers(self) -> List[Dict[str, Any]]:
        """List all phone numbers linked to your Bolna account."""
        response = self.client.get("/phone-numbers/all")
        return self._check_response(response)

    def delete_phone_number(self, number_id: str) -> None:
        """Delete a phone number from Bolna by its ID."""
        logger.info("Deleting phone number %s from Bolna", number_id)
        response = self.client.delete(f"/phone-numbers/{number_id}")
        self._check_response(response)

    # ── SIP Trunk Management (BYOT) ─────────────────────────────────── #

    def create_sip_trunk(
        self,
        name: str,
        provider: str,
        phone_number: str,
        gateway_address: str,
        auth_type: str = "userpass",
        auth_username: Optional[str] = None,
        auth_password: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Connect an external SIP trunk to Bolna (BYOT).

        Args:
            name:            Friendly trunk label
            provider:        Provider name (e.g. 'vobiz', 'twilio')
            phone_number:    E.164 format
            gateway_address: SIP gateway (e.g. 1e4ed098.sip.vobiz.ai)
            auth_type:       'userpass' or 'ip-based'
            auth_username:   SIP username (for userpass)
            auth_password:   SIP password (for userpass)
        """
        payload: Dict[str, Any] = {
            "name": name,
            "provider": provider,
            "gateways": [{"gateway_address": gateway_address}],
            "phone_numbers": [{"phone_number": phone_number}],
            "auth_type": auth_type,
        }
        if auth_username:
            payload["auth_username"] = auth_username
        if auth_password:
            payload["auth_password"] = auth_password

        logger.info(
            "Creating SIP trunk in Bolna | number=%s | gateway=%s",
            phone_number, gateway_address,
        )
        response = self.client.post("/sip-trunks/trunks", json=payload)
        return self._check_response(response)

    def list_sip_trunks(self) -> List[Dict[str, Any]]:
        """List all SIP trunks connected to your Bolna account."""
        response = self.client.get("/sip-trunks/trunks")
        return self._check_response(response)

    def update_sip_trunk(
        self, trunk_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing SIP trunk configuration."""
        response = self.client.patch(f"/sip-trunks/trunks/{trunk_id}", json=updates)
        return self._check_response(response)

    # ── Provider Connection (alternative to SIP Trunk) ───────────────── #

    # Maps friendly field names → Bolna API field names per provider
    PROVIDER_CREDENTIALS = {
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

    @classmethod
    def get_supported_providers(cls) -> List[str]:
        """Return list of supported provider names."""
        return list(cls.PROVIDER_CREDENTIALS.keys())

    @classmethod
    def get_required_fields(cls, provider: str) -> List[str]:
        """Return the required credential fields for a given provider."""
        cred_map = cls.PROVIDER_CREDENTIALS.get(provider)
        if not cred_map:
            raise ValueError(
                f"Unsupported provider '{provider}'. "
                f"Supported: {cls.get_supported_providers()}"
            )
        return list(cred_map.keys())

    def connect_provider(
        self,
        provider: str,
        credentials: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Connect a business's telephony provider to Bolna.

        Validates required fields, then POSTs each credential
        to Bolna's /providers endpoint.

        Args:
            provider:     Provider name (vobiz, twilio, plivo, exotel)
            credentials:  Dict of credential values keyed by friendly names
        """
        provider_lower = provider.lower()
        cred_map = self.PROVIDER_CREDENTIALS.get(provider_lower)
        if not cred_map:
            raise ValueError(
                f"Unsupported provider '{provider}'. "
                f"Supported: {self.get_supported_providers()}"
            )

        # Validate all required fields are provided
        required = set(cred_map.keys())
        provided = set(credentials.keys())
        missing = required - provided
        if missing:
            raise ValueError(
                f"Missing required fields for {provider}: {sorted(missing)}. "
                f"Required: {sorted(required)}"
            )

        # Send each credential to Bolna (auto-replace if already exists)
        results = []
        for friendly_name, bolna_name in cred_map.items():
            value = credentials[friendly_name]

            logger.info(
                "Setting provider credential | provider=%s | key=%s",
                provider, bolna_name,
            )

            response = self.client.post("/providers", json={
                "provider_name": bolna_name,
                "provider_value": value,
            })

            # 409 = credential already exists in Bolna, treat as success
            if response.status_code == 409:
                logger.info("Credential %s already exists, skipping", bolna_name)
                results.append({
                    "field": friendly_name,
                    "bolna_key": bolna_name,
                    "status": "already_exists",
                })
                continue

            self._check_response(response)
            results.append({
                "field": friendly_name,
                "bolna_key": bolna_name,
                "status": "saved",
            })

        logger.info(
            "Provider connected successfully | provider=%s | fields=%d",
            provider, len(results),
        )
        return {
            "provider": provider,
            "credentials_saved": len(results),
            "details": results,
        }

    def list_providers(self) -> Dict[str, Any]:
        """List all provider credentials stored in Bolna (values are masked)."""
        response = self.client.get("/providers")
        return self._check_response(response)

    def delete_provider(self, provider_id: str) -> Dict[str, Any]:
        """Delete a single provider credential from Bolna by its ID."""
        response = self.client.delete(f"/providers/{provider_id}")
        return self._check_response(response)

    def disconnect_provider(self, provider: str) -> Dict[str, Any]:
        """
        Remove ALL credentials for a given provider from Bolna.
        E.g. disconnect_provider("vobiz") deletes VOBIZ_API_KEY,
        VOBIZ_API_SECRET, and VOBIZ_PHONE_NUMBER.
        """
        provider_lower = provider.lower()
        cred_map = self.PROVIDER_CREDENTIALS.get(provider_lower)
        if not cred_map:
            raise ValueError(
                f"Unsupported provider '{provider}'. "
                f"Supported: {self.get_supported_providers()}"
            )

        # Get all credentials currently in Bolna
        existing = self.client.get("/providers").json()
        all_providers = existing.get("providers", [])

        # Find and delete all credentials that belong to this provider
        bolna_keys = set(cred_map.values())
        deleted = []
        for p in all_providers:
            if p.get("provider_name") in bolna_keys:
                resp = self.client.delete(f"/providers/{p['provider_id']}")
                logger.info(
                    "Deleted credential %s (%s) | status=%s",
                    p["provider_name"], p["provider_id"], resp.status_code,
                )
                deleted.append({
                    "bolna_key": p["provider_name"],
                    "provider_id": p["provider_id"],
                    "status": "deleted",
                })

        logger.info(
            "Provider disconnected | provider=%s | deleted=%d",
            provider, len(deleted),
        )
        return {
            "provider": provider,
            "credentials_deleted": len(deleted),
            "details": deleted,
        }
    # ── Batch Calling ────────────────────────────────────────────────── #
    def create_batch(
        self,
        csv_bytes: bytes,
        filename: str,
        agent_id: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:

        resolved_agent_id = agent_id or self.default_agent_id
        if not resolved_agent_id:
            raise BolnaConfigError("No agent ID provided and no default agent found")

        final_csv_bytes = csv_bytes

        if template_data:
            logger.info("Enriching CSV with template variables...")
            try:
                # 1. Read the original CSV from bytes into memory
                string_stream = io.StringIO(csv_bytes.decode('utf-8'))
                reader = csv.DictReader(string_stream)
                fieldnames = reader.fieldnames or []
                
                # 2. Add the template keys to the CSV header
                for key in template_data.keys():
                    if key not in fieldnames:
                        fieldnames.append(key)
                
                # 3. Create a new buffer to write the enriched CSV
                output_stream = io.StringIO()
                writer = csv.DictWriter(output_stream, fieldnames=fieldnames)
                writer.writeheader()
                
                # 4. Write every row, injecting the template data into it
                for row in reader:
                    for key, value in template_data.items():
                        row[key] = value
                    writer.writerow(row)
                
                # 5. Convert back to raw bytes for Bolna
                final_csv_bytes = output_stream.getvalue().encode('utf-8')
                logger.info("Successfully enriched CSV with template data.")
            except Exception as e:
                logger.error("Failed to parse and enrich CSV: %s", e)
                raise BolnaConfigError(f"Failed to process CSV with template: {e}")
        # -------------------------------------------------------------

        logger.info(
            "Creating batch | agent=%s | file=%s | contacts_approx=%s",
            resolved_agent_id, filename, final_csv_bytes.count(b"\n"),
        )

        response = httpx.post(
            f"{BOLNA_BASE_URL}/batches",
            headers={"Authorization": f"Bearer {self.api_key}"},
            data={"agent_id": resolved_agent_id},
            files={"file": (filename, final_csv_bytes, "text/csv")}, 
            timeout=30.0,
        )
        return self._check_response(response)


    def schedule_batch(
        self,
        batch_id: str,
        scheduled_at: str,
    ) -> Dict[str, Any]:
        logger.info("Scheduling batch | id =%s, | at=%s", batch_id, scheduled_at)
        
        # Determine if it's already an ISO string or a human-friendly format
        import dateutil.parser
        import pytz
        from datetime import datetime
        
        try:
            # Parse whatever format user supplied (dayfirst=True handles DD-MM-YY properly)
            dt = dateutil.parser.parse(scheduled_at, dayfirst=True)
            
            # If no timezone is provided, assume IST (Asia/Kolkata) since that's your local time
            ist_tz = pytz.timezone("Asia/Kolkata")
            if dt.tzinfo is None:
                dt = ist_tz.localize(dt)
            
            # Check if the scheduled time is in the past
            now_dt = datetime.now(ist_tz)
            if dt < now_dt:
                raise ValueError(f"Cannot schedule a batch in the past. Current time is {now_dt.strftime('%d-%m-%y %I:%M %p %Z')}")
                
            # Convert to UTC which Bolna expects, and format to ISO 8601 string
            utc_dt = dt.astimezone(pytz.UTC)
            # Bolna's backend crashes on .000Z. It needs strict Python fromisoformat style.
            final_iso_time = utc_dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            logger.info("Converted time to ISO: %s", final_iso_time)
            
        except Exception as e:
            logger.error("Could not parse datetime string: %s", e)
            raise BolnaConfigError(f"Invalid datetime format: {scheduled_at}. Error: {e}")

        # We must use httpx.post directly here as well because self.client has 
        # Content-Type: application/json forced, but Bolna expects form data here.
        response = httpx.post(
            f"{BOLNA_BASE_URL}/batches/{batch_id}/schedule",
            headers={"Authorization": f"Bearer {self.api_key}"},
            data={"scheduled_at": final_iso_time},
            timeout=30.0,
        )
        return self._check_response(response)

    def get_batch(self, batch_id: str) -> Dict[str, Any]:
        response = self.client.get(f"/batches/{batch_id}")
        return self._check_response(response)

    def list_batches(self) -> List[Dict[str, Any]]:
        response = self.client.get("/batches")
        return self._check_response(response)

    def stop_batch(self, batch_id: str) -> Dict[str, Any]:
        logger.info("Stopping batch | id =%s", batch_id)
        response = self.client.post(f"/batches/{batch_id}/stop")
        return self._check_response(response)

    def get_batch_executions(self, batch_id: str) -> List[Dict[str, Any]]:
        response = self.client.get(f"/batches/{batch_id}/executions")
        return self._check_response(response)