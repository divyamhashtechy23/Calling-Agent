"""
Main Application — FastAPI entry point.

WHAT CHANGED:
    - Swapped 'retell_routes' import → 'bolna_routes'
    - Updated app description from "Retell AI" → "Bolna AI"
    - Updated root endpoint to show Bolna API paths
    - Updated /config/check to show Bolna environment variables
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import bolna_routes        # ← was: retell_routes
from routes import call_tracking_routes
from app.database import engine
from app.models import Base
from dotenv import load_dotenv
import logging
import os

load_dotenv()

# ------------------------------------------------------------------ #
#  Logging                                                            #
# ------------------------------------------------------------------ #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  DB init                                                            #
# ------------------------------------------------------------------ #
Base.metadata.create_all(bind=engine)

# ------------------------------------------------------------------ #
#  App                                                                #
# ------------------------------------------------------------------ #
app = FastAPI(
    title="Outbound AI Calling Agent",
    description=(
        "Backend service for AI-powered outbound calling via Bolna AI. "
        "Supports real phone calls with automated STT → LLM → TTS conversation."
    ),
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------ #
#  Routers                                                            #
# ------------------------------------------------------------------ #

# ✅ Bolna AI — primary integration
app.include_router(bolna_routes.router)

# ✅ Call Tracking — AiCallTracking GET API (SQL Server)
app.include_router(call_tracking_routes.router)


# ------------------------------------------------------------------ #
#  Root & Config                                                      #
# ------------------------------------------------------------------ #

@app.get("/", tags=["Health"])
def root():
    return {
        "message": "Outbound AI Calling Agent is running",
        "version": "4.0.0",
        "powered_by": "Bolna AI",
        "docs": "/docs",
        "quick_start": {
            "step_1_connect_number": "POST /api/bolna/sip-trunks  (connect your SIP trunk number)",
            "step_2_initiate_call":  "POST /api/bolna/call",
            "step_3_list_calls":     "GET  /api/bolna/calls",
            "step_4_view_call":      "GET  /api/bolna/calls/{call_id}",
            "webhook":               "POST /webhook/bolna  (set this URL in Bolna agent Analytics tab)",
        },
    }


@app.get("/config/check", tags=["Health"])
def check_config():
    """Check that all required environment variables are loaded."""
    bolna_key    = os.getenv("BOLNA_API_KEY", "")
    agent_id     = os.getenv("BOLNA_AGENT_ID", "")
    from_number  = os.getenv("BOLNA_FROM_NUMBER", "")
    webhook_base = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000")

    return {
        "status": "ok",
        "bolna_api_key_loaded": bool(bolna_key),
        "bolna_api_key_prefix": bolna_key[:10] + "..." if bolna_key else None,
        "bolna_agent_id": agent_id or "⚠️  NOT SET — add BOLNA_AGENT_ID to .env",
        "bolna_from_number": from_number or "⚠️  NOT SET — add BOLNA_FROM_NUMBER to .env",
        "webhook_base_url": webhook_base,
        "bolna_webhook_url": f"{webhook_base}/webhook/bolna",
        "database_url": os.getenv("DATABASE_URL"),
        "note": "Set the webhook URL in Bolna Agent → Analytics Tab → Webhook URL",
    }
