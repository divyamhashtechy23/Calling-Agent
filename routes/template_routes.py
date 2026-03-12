import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.schemas import TemplateCreate, TemplateResponse
from services.template_service import create_template, get_template, get_templates_by_user, list_all_templates

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/api/templates", response_model=TemplateResponse, summary="Create a new Campaign Template")
async def create_new_template(template: TemplateCreate, db: Session = Depends(get_db)):
    try:
        return create_template(db, template)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/templates", response_model=List[TemplateResponse], summary="List all Campaign Templates")
async def get_all_templates(db: Session = Depends(get_db)):
    return list_all_templates(db)

@router.get("/api/templates/{temp_id}", response_model=TemplateResponse, summary="Get a Campaign Template by ID")
async def get_single_template(temp_id: int, db: Session = Depends(get_db)):
    template = get_template(db, temp_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {temp_id} not found")
    return template
