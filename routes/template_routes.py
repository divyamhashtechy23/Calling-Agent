import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, DataError, IntegrityError

from app.mssql_database import get_mssql_session # <- MSSQL session import
from app.schemas import TemplateCreate, TemplateUpdate, TemplateResponse, ApiResponse
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

@router.post("/api/templates", response_model=ApiResponse, status_code=200)
async def create_new_template(template: TemplateCreate, db: Session = Depends(get_mssql_db)):
    """Create a new AI calling template."""
    try:
        result = create_template(db, template)
        return ApiResponse(
            success=True,
            message="Template created successfully.",
            data=TemplateResponse.model_validate(result).model_dump()
        )
    except OperationalError as e:
        logger.error("DB connection error while creating template: %s", e)
        raise HTTPException(status_code=503, detail="Database connection failed. Please try again later.")
    except DataError as e:
        logger.error("Data error while creating template: %s", e)
        raise HTTPException(status_code=422, detail="One or more fields exceed the allowed length. Please shorten your input.")
    except IntegrityError as e:
        logger.error("Integrity error while creating template: %s", e)
        raise HTTPException(status_code=409, detail="A template with this name already exists for this user.")
    except Exception as e:
        logger.error("Unexpected error while creating template: %s", e)
        raise HTTPException(status_code=500, detail="Something went wrong while creating the template. Please try again.")

@router.get("/api/templates", response_model=ApiResponse)
async def get_all_templates(db: Session = Depends(get_mssql_db)):
    """List every campaign template"""
    try:
        results = list_all_templates(db)
        return ApiResponse(
            success=True,
            message=f"{len(results)} template(s) fetched successfully.",
                data=[TemplateResponse.model_validate(t).model_dump() for t in results]
        )
    except OperationalError as e:
        logger.error("DB connection error while fetching templates: %s", e)
        raise HTTPException(status_code=503, detail="Database connection failed. Please try again later.")
    except Exception as e:
        logger.error("Unexpected error while fetching templates: %s", e)
        raise HTTPException(status_code=500, detail="Something went wrong while fetching templates. Please try again.")

@router.get("/api/templates/user/{user_id}", response_model=ApiResponse)
async def get_user_templates(user_id: str, db:Session = Depends(get_mssql_db)):
    """List all templates belonging to a specific user."""
    try:
        results = get_templates_by_user(db, user_id)
        return ApiResponse(
            success=True,
            message=f"{len(results)} template(s) found for user.",
                data=[TemplateResponse.model_validate(t).model_dump() for t in results]
        )
    except OperationalError as e:
        logger.error("DB connection error while fetching templates for user %s: %s", user_id, e)
        raise HTTPException(status_code=503, detail="Database connection failed. Please try again later.")
    except Exception as e:
        logger.error("Unexpected error while fetching templates for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail="Something went wrong while fetching user templates. Please try again.")

@router.get("/api/templates/{template_id}", response_model=ApiResponse)
async def get_single_template(template_id: int, db:Session = Depends(get_mssql_db)):
    """Get a single template by its ID."""
    try:
        template = get_template(db, template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template with ID {template_id} was not found.")
        return ApiResponse(
            success=True,
            message="Template fetched successfully.",
            data=TemplateResponse.model_validate(template).model_dump()
        )
    except HTTPException:
        raise
    except OperationalError as e:
        logger.error("DB connection error while fetching template %s: %s", template_id, e)
        raise HTTPException(status_code=503, detail="Database connection failed. Please try again later.")
    except Exception as e:
        logger.error("Unexpected error while fetching template %s: %s", template_id, e)
        raise HTTPException(status_code=500, detail="Something went wrong while fetching the template. Please try again.")

@router.put("/api/templates/{template_id}", response_model=ApiResponse)
async def update_existing_template(template_id: int, data: TemplateUpdate, db: Session = Depends(get_mssql_db)):
    """Partially update a template — only fields you send will be changed."""
    try:
        template = update_template(db, template_id, data)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template with ID {template_id} was not found.")
        return ApiResponse(
            success=True,
            message="Template updated successfully.",
            data=TemplateResponse.model_validate(template).model_dump()
        )
    except HTTPException:
        raise
    except OperationalError as e:
        logger.error("DB connection error while updating template %s: %s", template_id, e)
        raise HTTPException(status_code=503, detail="Database connection failed. Please try again later.")
    except DataError as e:
        logger.error("Data error while updating template %s: %s", template_id, e)
        raise HTTPException(status_code=422, detail="One or more fields exceed the allowed length. Please shorten your input.")
    except Exception as e:
        logger.error("Unexpected error while updating template %s: %s", template_id, e)
        raise HTTPException(status_code=500, detail="Something went wrong while updating the template. Please try again.")

@router.delete("/api/templates/{template_id}", response_model=ApiResponse, status_code=200)
async def delete_existing_template(template_id: int, db: Session = Depends(get_mssql_db)):
    """Permanently delete a template."""
    try:
        deleted = delete_template(db, template_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Template with ID {template_id} was not found.")
        return ApiResponse(
            success=True,
            message=f"Template {template_id} deleted successfully.",
            data=None
        )
    except HTTPException:
        raise
    except OperationalError as e:
        logger.error("DB connection error while deleting template %s: %s", template_id, e)
        raise HTTPException(status_code=503, detail="Database connection failed. Please try again later.")
    except Exception as e:
        logger.error("Unexpected error while deleting template %s: %s", template_id, e)
        raise HTTPException(status_code=500, detail="Something went wrong while deleting the template. Please try again.")


