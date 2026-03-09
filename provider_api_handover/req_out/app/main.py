from fastapi import FastAPI
from app.routes import calls, costs, meta, webhooks, providers

app = FastAPI(
    title="AI Calling Service",
    version="2.0.0"
)

# Core APIs
app.include_router(calls.router, prefix="/v1/calls")
app.include_router(costs.router, prefix="/v1/costs")
app.include_router(meta.router, prefix="/v1")

# Provider & SIP trunk management
app.include_router(providers.router, prefix="/v1/providers")

# Webhooks (Bolna)
app.include_router(webhooks.router, prefix="/webhooks")

@app.get("/health")
def health():
    return {"status": "ok"}
