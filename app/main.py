from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import retell_routes
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
        "Backend service for AI-powered outbound calling via Retell AI. "
        "Supports real phone calls with automated STT → LLM → TTS conversation."
    ),
    version="3.0.0",
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

# ✅ Retell AI — primary integration
app.include_router(retell_routes.router)


# ------------------------------------------------------------------ #
#  Root & Config                                                      #
# ------------------------------------------------------------------ #

@app.get("/", tags=["Health"])
def root():
    return {
        "message": "Outbound AI Calling Agent is running",
        "version": "3.0.0",
        "docs": "/docs",
        "quick_start": {
            "step_1_initiate_call": "POST /api/retell/call",
            "step_2_list_calls":    "GET  /api/retell/calls",
            "step_3_view_call":     "GET  /api/retell/calls/{call_id}",
            "webhook":              "POST /webhook/retell  (set this URL in Retell dashboard)",
        },
    }


@app.get("/config/check", tags=["Health"])
def check_config():
    """Check that all required environment variables are loaded."""
    retell_key  = os.getenv("RETELL_API_KEY", "")
    agent_id    = os.getenv("RETELL_AGENT_ID", "")
    from_number = os.getenv("RETELL_FROM_NUMBER", "")
    webhook_base = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000")

    return {
        "status": "ok",
        "retell_api_key_loaded": bool(retell_key),
        "retell_api_key_prefix": retell_key[:10] + "..." if retell_key else None,
        "retell_agent_id": agent_id or "⚠️  NOT SET — add RETELL_AGENT_ID to .env",
        "retell_from_number": from_number or "⚠️  NOT SET — add RETELL_FROM_NUMBER to .env",
        "webhook_base_url": webhook_base,
        "retell_webhook_url": f"{webhook_base}/webhook/retell",
        "database_url": os.getenv("DATABASE_URL"),
        "note": "Set the webhook URL in Retell Dashboard → Settings → Webhooks",
    }
