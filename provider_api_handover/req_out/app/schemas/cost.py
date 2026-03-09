from pydantic import BaseModel

class CostItem(BaseModel):
    callId: str
    amount: float
