# Provider Connection API — Flow & Documentation

**Module:** Telephony Provider Integration
**Purpose:** Connect business phone numbers to Bolna AI through their existing telephony provider

---

## Overview

This API allows businesses to connect their telephony provider credentials (VoBiz, Twilio, Plivo, Exotel) to Bolna AI. Once connected, Bolna can make/receive AI-powered calls through the business's own phone number.

---

## Flow Diagram

```
Business User
     │
     │  1. "Which providers do you support?"
     ▼
GET /api/bolna/providers/supported
     │
     │  Response: ["vobiz", "twilio", "plivo", "exotel"]
     │
     │  2. "What credentials do I need for VoBiz?"
     ▼
GET /api/bolna/providers/fields/vobiz
     │
     │  Response: ["api_key", "api_secret", "phone_number"]
     │
     │  3. "Here are my credentials"
     ▼
POST /api/bolna/providers/connect
     │  Body: {"provider": "vobiz", "credentials": {...}}
     │
     │  Our backend validates → sends each credential to Bolna
     │
     ▼
✅ Provider connected! Business phone number is now available in Bolna.
```

---

## API Endpoints

### 1. Connect a Provider

**`POST /api/bolna/providers/connect`**

Connects a business's telephony provider by saving their API credentials to Bolna.

**How it works internally:**
1. Receives provider name + credentials from the business
2. Looks up the provider in our registry to find required fields
3. Validates all required fields are present
4. Sends each credential to Bolna's `/providers` API as a key-value pair
5. If a credential already exists (409), skips it gracefully

**Request:**
```json
{
  "provider": "vobiz",
  "credentials": {
    "api_key": "MA_OKKPN9FH",
    "api_secret": "G2yyImAEVYLv...",
    "phone_number": "+917971543244"
  }
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Provider 'vobiz' connected successfully!",
  "provider": "vobiz",
  "credentials_saved": 3,
  "details": [
    {"field": "api_key", "bolna_key": "VOBIZ_API_KEY", "status": "saved"},
    {"field": "api_secret", "bolna_key": "VOBIZ_API_SECRET", "status": "saved"},
    {"field": "phone_number", "bolna_key": "VOBIZ_PHONE_NUMBER", "status": "saved"}
  ]
}
```

**Validation Error (400):**
```json
{
  "detail": "Missing required fields for vobiz: ['api_secret']. Required: ['api_key', 'api_secret', 'phone_number']"
}
```

**Provider-specific credential fields:**

| Provider | Required Fields |
|----------|----------------|
| VoBiz | `api_key`, `api_secret`, `phone_number` |
| Twilio | `account_sid`, `auth_token`, `phone_number` |
| Plivo | `auth_id`, `auth_token`, `phone_number` |
| Exotel | `api_key`, `api_token`, `account_sid`, `domain`, `phone_number`, `outbound_app_id`, `inbound_app_id` |

---

### 2. Get Connection Status

**`GET /api/bolna/providers`**

Returns all provider credentials currently stored in Bolna. Credential values are masked for security.

**Response (200):**
```json
{
  "success": true,
  "providers": {
    "providers": [
      {
        "provider_id": "f3d148aa-210c-44fc-9c7b-cd673c183db2",
        "provider_name": "VOBIZ_API_KEY",
        "provider_value": "xxxxxxN9FH"
      },
      {
        "provider_id": "a2b3...",
        "provider_name": "VOBIZ_API_SECRET",
        "provider_value": "xxxxxxVnZk"
      },
      {
        "provider_id": "c4d5...",
        "provider_name": "VOBIZ_PHONE_NUMBER",
        "provider_value": "+917971543244"
      }
    ]
  }
}
```

**Helper endpoints:**

| Endpoint | Purpose |
|----------|---------|
| `GET /api/bolna/providers/supported` | List all supported provider names |
| `GET /api/bolna/providers/fields/{provider}` | Get required fields for a specific provider |

---

### 3. Disconnect a Provider

**`DELETE /api/bolna/providers/disconnect/{provider}`**

Removes ALL credentials for a given provider from Bolna in one call.

**Example:** `DELETE /api/bolna/providers/disconnect/vobiz`

**How it works internally:**
1. Looks up which Bolna keys belong to "vobiz" (VOBIZ_API_KEY, VOBIZ_API_SECRET, VOBIZ_PHONE_NUMBER)
2. Fetches all stored credentials from Bolna
3. Finds and deletes each matching credential
4. Returns a summary of what was deleted

**Response (200):**
```json
{
  "success": true,
  "message": "Provider 'vobiz' disconnected — 3 credentials removed.",
  "provider": "vobiz",
  "credentials_deleted": 3,
  "details": [
    {"bolna_key": "VOBIZ_API_KEY", "provider_id": "f3d1...", "status": "deleted"},
    {"bolna_key": "VOBIZ_API_SECRET", "provider_id": "a2b3...", "status": "deleted"},
    {"bolna_key": "VOBIZ_PHONE_NUMBER", "provider_id": "c4d5...", "status": "deleted"}
  ]
}
```

After disconnecting, the business can reconnect with new/updated credentials using `POST /connect`.

---

## Code Structure

```
services/
  └── bolna_service.py     ← Business logic, provider registry, Bolna API calls
app/
  ├── schemas.py            ← Request validation (ConnectProviderRequest)
  └── models.py             ← Database models
routes/
  └── bolna_routes.py       ← HTTP endpoint handlers
```

### Key Design: Provider Registry

The system uses a registry dictionary that maps each provider to its required fields and corresponding Bolna API names:

```python
PROVIDER_CREDENTIALS = {
    "vobiz": {
        "api_key":      "VOBIZ_API_KEY",       # Business sends "api_key"
        "api_secret":   "VOBIZ_API_SECRET",     # Bolna stores as "VOBIZ_API_SECRET"
        "phone_number": "VOBIZ_PHONE_NUMBER",
    },
    "twilio": { ... },
    "plivo": { ... },
    "exotel": { ... },
}
```

**Adding a new provider** requires only adding a new entry to this dictionary. No other code changes needed.

---

## Scalability

| Scenario | Effort Required |
|----------|-----------------|
| Add a new provider (e.g. Telnyx) | Add 1 dictionary entry (~5 lines) |
| Add a new credential field | Add 1 key-value pair to existing entry |
| Frontend form for new provider | Zero changes (form builds dynamically) |
