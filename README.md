# 📞 Outbound AI Calling Agent

An AI-powered outbound calling backend built with **FastAPI** and **Retell AI**.  
The system initiates phone calls, manages a full voice conversation (STT → LLM → TTS), and saves transcripts, summaries, and recordings — all automatically.

---

## 📁 Project Structure

```
Calling-Agent/
├── app/
│   ├── database.py        # SQLAlchemy engine & session setup (SQLite)
│   ├── main.py            # FastAPI entry point, CORS, router registration
│   ├── models.py          # Call model (DB schema)
│   └── schemas.py         # Pydantic request models for all endpoints
├── routes/
│   ├── __init__.py
│   └── retell_routes.py   # All API endpoints (calls, webhooks, phone management)
├── services/
│   ├── __init__.py
│   └── retell_service.py  # Retell SDK wrapper (call creation, phone import)
├── .env                   # Environment variables (API keys, config)
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

---

## ⚙️ Prerequisites

| Requirement        | Details                                                              |
| ------------------ | -------------------------------------------------------------------- |
| **Python**         | 3.10+ recommended                                                    |
| **Retell AI Account** | Sign up at [retellai.com](https://www.retellai.com)               |
| **ngrok**          | For exposing your localhost to the internet (webhooks)                |
| **VoBiz Account**  | *(Optional)* For connecting real phone numbers via SIP trunking      |

---

## 🚀 Getting Started

### 1. Clone & Install

```bash
git clone <repo-url>
cd Calling-Agent

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure `.env`

Create a `.env` file in the project root (or edit the existing one):

```env
# Database
DATABASE_URL=sqlite:///./calling_agent.db

# Retell AI (required)
RETELL_API_KEY=your_retell_api_key_here
RETELL_AGENT_ID=your_retell_agent_id_here
RETELL_FROM_NUMBER=+91XXXXXXXXXX

# Webhook (required for call events)
WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok-free.app

# VoBiz SIP Trunk (optional — only if using VoBiz phone numbers)
VOBIZ_TERMINATION_URI=your-trunk-id.sip.vobiz.ai
VOBIZ_SIP_USERNAME=your_sip_username
VOBIZ_SIP_PASSWORD=your_sip_password
```

> **Where to find these values:**
>
> | Variable             | Where to get it                                                    |
> | -------------------- | ------------------------------------------------------------------ |
> | `RETELL_API_KEY`     | Retell Dashboard → **Settings** → **API Keys**                     |
> | `RETELL_AGENT_ID`    | Retell Dashboard → **Agents** → click your agent → copy the ID    |
> | `RETELL_FROM_NUMBER` | Your imported phone number in E.164 format (e.g. `+919XXXXXXXX`)  |
> | `WEBHOOK_BASE_URL`   | Your ngrok public URL (see Step 4)                                 |

### 3. Start the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API docs will be available at: **http://localhost:8000/docs**

### 4. Expose via ngrok (for Webhooks)

In a separate terminal:

```bash
ngrok http 8000
```

Copy the `https://xxxx.ngrok-free.app` URL and:
1. Paste it into your `.env` as `WEBHOOK_BASE_URL`
2. Set it in **Retell Dashboard → Settings → Webhooks** as:  
   `https://xxxx.ngrok-free.app/webhook/retell`

---

## 🔧 Retell AI Setup Guide

Before making calls, you need to set up your agent in the Retell Dashboard:

### Step 1 — Create an Agent
1. Go to [Retell Dashboard](https://dashboard.retellai.com) → **Agents** → **Create Agent**
2. Choose a voice, set the language, write your agent prompt
3. Copy the **Agent ID** → paste into `.env` as `RETELL_AGENT_ID`

### Step 2 — Set Your Webhook
1. Go to **Settings** → **Webhooks**
2. Set the webhook URL to: `https://<your-ngrok-url>/webhook/retell`
3. This URL receives call events (`call_started`, `call_ended`, `call_analyzed`)

### Step 3 — Get Your API Key
1. Go to **Settings** → **API Keys**
2. Copy the key → paste into `.env` as `RETELL_API_KEY`

### Step 4 — Connect a Phone Number *(Optional)*

You can test without a phone number using the **Web Call** endpoint.  
To make real phone calls, you need a number from VoBiz (or another SIP provider):

#### VoBiz Setup:
1. Log in to [vobiz.ai](https://vobiz.ai) → **SIP Trunks** → Create a trunk
2. Note the **Trunk ID** (your termination URI = `<trunkId>.sip.vobiz.ai`)
3. Under **Credentials** → create a SIP username and password
4. Under **Origination URIs** → add: `sip:sip.retellai.com`
5. Under **Phone Numbers** → assign your number to the trunk
6. Use the `POST /api/retell/phone-number/import` endpoint to register it with Retell

---

## 📡 API Endpoints

All endpoints are accessible via the Swagger UI at `/docs`.

### Calling

| Method | Endpoint                          | Description                                    |
| ------ | --------------------------------- | ---------------------------------------------- |
| POST   | `/api/retell/call`                | Initiate an outbound phone call                |
| POST   | `/api/retell/web-call`            | Create a browser-based test call (free)        |
| GET    | `/api/retell/calls`               | List all calls (newest first)                  |
| GET    | `/api/retell/calls/{call_id}`     | Get a single call with transcript & summary    |

### Webhook

| Method | Endpoint           | Description                                         |
| ------ | ------------------ | --------------------------------------------------- |
| POST   | `/webhook/retell`  | Receives Retell events (set in Retell Dashboard)     |

### Phone Number Management

| Method | Endpoint                                      | Description                                |
| ------ | --------------------------------------------- | ------------------------------------------ |
| POST   | `/api/retell/phone-number/connect`           | Connect a SIP trunk number into Retell     |
| GET    | `/api/retell/phone-numbers`                    | List all registered phone numbers          |
| DELETE  | `/api/retell/phone-number/{phone_number}`     | Remove a number from Retell                |

### Health

| Method | Endpoint         | Description                                  |
| ------ | ---------------- | -------------------------------------------- |
| GET    | `/`              | Health check + quick start guide             |
| GET    | `/config/check`  | Verify all env vars are loaded correctly     |

---

## 🧪 Testing the API

### Test 1 — Verify Config (No API key needed)

```bash
curl http://localhost:8000/config/check
```

You should see all your environment variables loaded correctly.

### Test 2 — Web Call (Free, No Phone Number Needed)

```bash
curl -X POST http://localhost:8000/api/retell/web-call \
  -H "Content-Type: application/json" \
  -d '{"lead_name": "Test User"}'
```

This returns an `access_token` and `test_url`. Open the `test_url` in your browser to talk to your agent.

### Test 3 — Outbound Phone Call (Requires Phone Number)

```bash
curl -X POST http://localhost:8000/api/retell/call \
  -H "Content-Type: application/json" \
  -d '{
    "to_number": "+919XXXXXXXX",
    "lead_name": "John Doe",
    "lead_id": "lead_001"
  }'
```

> **Note:** You need a valid `RETELL_FROM_NUMBER` in `.env` or pass `from_number` in the request body.

### Test 4 — Connect a SIP Trunk Phone Number (Any Provider)

```bash
curl -X POST http://localhost:8000/api/retell/phone-number/connect \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+919XXXXXXXX",
    "termination_uri": "your-trunk-id.sip.provider.com",
    "sip_trunk_username": "your_username",
    "sip_trunk_password": "your_password",
    "nickname": "My Office Line"
  }'
```

### Test 5 — List Calls & View Transcript

```bash
# List all calls
curl http://localhost:8000/api/retell/calls

# Get a specific call (with transcript + summary)
curl http://localhost:8000/api/retell/calls/{call_id}
```

---

## 🗄️ Database Schema

The app uses **SQLite** by default. The `calls` table stores:

| Column           | Type     | Description                                      |
| ---------------- | -------- | ------------------------------------------------ |
| `id`             | String   | UUID primary key                                 |
| `lead_id`        | String   | Your internal lead identifier                    |
| `lead_name`      | String   | Customer name                                    |
| `lead_phone`     | String   | Customer phone number                            |
| `retell_call_id` | String   | Retell's call ID (links to their system)         |
| `status`         | String   | `queued` → `initiated` → `ongoing` → `ended`    |
| `transcript`     | Text     | Full conversation transcript (from webhook)      |
| `call_summary`   | Text     | AI-generated call summary (from webhook)         |
| `recording_url`  | String   | Link to call recording (from webhook)            |
| `duration_ms`    | Integer  | Call duration in milliseconds                    |
| `created_at`     | DateTime | When the call was created                        |

> The database file `calling_agent.db` is auto-created on first run. Delete it to reset.

---

## 🔄 How It All Works

```
┌─────────────┐    POST /api/retell/call    ┌──────────────┐
│  Your App   │ ──────────────────────────→ │  This Server │
│  (Frontend) │                             │  (FastAPI)   │
└─────────────┘                             └──────┬───────┘
                                                   │
                                          Retell SDK call
                                                   │
                                                   ▼
                                          ┌──────────────┐
                                          │  Retell AI   │
                                          │  (Cloud)     │
                                          └──────┬───────┘
                                                 │
                                    Calls the customer's phone
                                    AI handles full conversation
                                                 │
                                                 ▼
                                    POST /webhook/retell
                                    (call_started, call_ended,
                                     call_analyzed events)
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │   SQLite DB  │
                                          │  (calls tbl) │
                                          └──────────────┘
                                    Transcript, summary, recording
                                    saved automatically
```

---

## 🛑 Troubleshooting

| Problem                          | Solution                                                        |
| -------------------------------- | --------------------------------------------------------------- |
| `ModuleNotFoundError: retell`    | Run `pip install retell-sdk` inside your `.venv`                |
| Webhook not receiving events     | Check ngrok is running & URL is set in Retell Dashboard         |
| `RETELL_API_KEY not set`         | Add your key to `.env` and restart the server                   |
| Call created but no transcript   | Wait 30s after call ends — `call_analyzed` event may be delayed |
| `422 Unprocessable Entity`       | Check the request body matches the schema in `/docs`            |

---

## 📝 Notes for the Developer

- **No frontend included** — this is a pure API backend. Use the Swagger UI at `/docs` for testing.
- **SQLite is the default DB** — swap `DATABASE_URL` in `.env` for PostgreSQL if scaling.
- **`ngrok.exe`** is included in the repo for convenience. Run it directly or install globally.
- **The webhook URL changes every time** you restart ngrok (unless on a paid plan). Update it in both `.env` and the Retell Dashboard.
- **Web Calls are free** and don't require a phone number — great for development and testing.
