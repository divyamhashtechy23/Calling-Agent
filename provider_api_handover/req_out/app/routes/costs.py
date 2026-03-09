from fastapi import APIRouter

router = APIRouter()

@router.get("/summary")
def cost_summary():
    return {
        "message": "cost summary placeholder"
    }
