import logging
from sqlalchemy.orm import Session
from app.models import AiCallingTemplate
from app.schemas import TemplateCreate, TemplateUpdate

logger = logging.getLogger(__name__)

def create_template(db: Session,data: TemplateCreate) -> AiCallingTemplate:
    db_template = AiCallingTemplate(
        user_id=data.user_id,
        template_name=data.template_name,
        industry=data.industry,
        language=data.language or "en",
        org_name = data.org_name,
        caller_name=data.caller_name,
        call_purpose=data.call_purpose,
        call_script=data.call_script,
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    logger.info("Created template id=%s for user=%s",db_template.template_id, db_template.user_id)
    return db_template

def get_template(db:Session, template_id: int) -> AiCallingTemplate | None:
    return db.query(AiCallingTemplate).filter(AiCallingTemplate.template_id == template_id).first()

def get_templates_by_user(db: Session, user_id: str) -> list[AiCallingTemplate]:
    """ Fetch all templates belonging to a specific user. """
    return db.query(AiCallingTemplate).filter(AiCallingTemplate.user_id == user_id).all()

def list_all_templates(db: Session) -> list[AiCallingTemplate]:
    """Fetch every template in the table."""
    return db.query(AiCallingTemplate).all()

def update_template(db: Session, template_id: int, data: TemplateUpdate) -> AiCallingTemplate | None:
    """
    Update an existing template with new data.
    Only fields provided in the update request will be modified.
    """
    db_template = get_template(db, template_id)
    if not db_template:
        logger.warning("Attempted to update non-existent template id=%s", template_id)
        return None
    
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_template, field, value)

    db.commit()
    db.refresh(db_template)
    logger.info("Updated template id=%s", template_id)
    return db_template

def delete_template(db: Session, template_id: int) -> bool:
    """
    Removes a template from the database. Returns True if deletion was successful, False if the template was not found.
    """
    db_template = get_template(db, template_id)
    if not db_template:
        logger.warning("Attempted to delete non-existent template id=%s", template_id)
        return False
    
    db.delete(db_template)
    db.commit()
    logger.info("Deleted template id=%s", template_id)
    return True