import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.mssql_database import get_mssql_session # <- MSSQL session import
from app.schemas import TemplateCreate, TemplateUpdate, TemplateResponse
from services.template_service import (
    create_template,
    get_template,
    get_templates_by_user,
    list_all_templates,
    update_template,
    delete_template
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Dependency ──────────────────────────────────────────────────────── #

def get_mssql_db():
    """Providing a MSSQL database session for route handlers."""
    db = get_mssql_session()
    try:
        yield db
    finally:
        db.close()

# ── Endpoints ───────────────────────────────────────────────────────── #

@router.post("/api/templates", response_model=TemplateResponse, status_code=201)
async def create_new_template(template: TemplateCreate, db: Session = Depends(get_mssql_db)):
    """Create a new AI calling template."""
    try:
        return create_template(db, template)
    except Exception as e:
        logger.error("Failed to create template: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/templates", response_model=List[TemplateResponse])
async def get_all_templates(db: Session = Depends(get_mssql_db)):
    """List every campaign template"""
    return list_all_templates(db)

@router.get("/api/templates/user/{user_id}", response_model=List[TemplateResponse])
async def get_user_templates(user_id: str, db:Session = Depends(get_mssql_db)):
    """List all templates belonging to a specific user. """
    return get_templates_by_user(db, user_id)

@router.get("/api/templates/{template_id}", response_model=TemplateResponse)
async def get_single_template(template_id: int, db:Session = Depends(get_mssql_db)):
    """Get a single template by its ID."""
    template = get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    return template

@router.put("/api/templates/{template_id}", response_model=TemplateResponse)
async def update_existing_template(template_id: int, data: TemplateUpdate, db: Session = Depends(get_mssql_db)):
    """
    Partially update a template - only fields you send will be changes
    """
    template = update_template(db, template_id, data)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    return template

@router.delete("/api/templates/{template_id}", status_code=204)
async def delete_existing_template(template_id: int, db: Session = Depends(get_mssql_db)):
    """
    Deleting a template premanaently
    """
    deleted = delete_template(db, template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=
                            f"Template {template_id} not found")


