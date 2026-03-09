from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    SERVICE_API_KEY = os.getenv("SERVICE_API_KEY", "dev-key")
    BOLNA_API_KEY = os.getenv("BOLNA_API_KEY", "")
    BOLNA_BASE_URL = os.getenv("BOLNA_BASE_URL", "https://api.bolna.ai")
    BOLNA_START_CALL_PATH = os.getenv("BOLNA_START_CALL_PATH", "/call")
    BOLNA_EXECUTION_PATH_TEMPLATE = os.getenv(
        "BOLNA_EXECUTION_PATH_TEMPLATE",
        "/executions/{execution_id}",
    )
    BOLNA_WEBHOOK_SECRET = os.getenv("BOLNA_WEBHOOK_SECRET", "")
    BOLNA_AGENT_EN = os.getenv("BOLNA_AGENT_EN", "")
    BOLNA_AGENT_HI = os.getenv("BOLNA_AGENT_HI", "")
    BOLNA_AGENT_GU = os.getenv("BOLNA_AGENT_GU", "")
    DOTNET_WEBHOOK_URL = os.getenv("DOTNET_WEBHOOK_URL", "")
    IDEMPOTENCY_TTL_SECONDS = int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "1800"))

settings = Settings()
