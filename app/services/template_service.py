import logging
from sqlalchemy.orm import Session
from app.models import CampaignTemplate
from app.schemas import TemplateCreate

logger = logging.getLogger(__name__)

def create_template(db: Session, template_data: TemplateCreate) -> CampaignTemplate:
    """Saves a new Campaign Template to the database."""
    try:
        db_template = CampaignTemplate(
            template_name=template_data.template_name,
            industry=template_data.industry,
            language=template_data.language,
            org_name=template_data.org_name,
            caller_name=template_data.caller_name,
            call_purpose=template_data.call_purpose,
            call_script=template_data.call_script
        )
        db.add(db_template)
        db.commit()
        db.refresh(db_template)
        logger.info("Successfully created template: %s (ID: %s)", db_template.template_name, db_template.temp_id)
        return db_template
    except Exception as e:
        db.rollback()
        logger.error("Error creating template: %s", e)
        raise e

def get_template(db: Session, temp_id: int) -> CampaignTemplate:
    """Retrieves a specific Template by its temp_id."""
    return db.query(CampaignTemplate).filter(CampaignTemplate.temp_id == temp_id).first()

def get_templates_by_user(db: Session, user_id: str):
    """Retrieves all templates for a specific user."""
    return db.query(CampaignTemplate).filter(CampaignTemplate.user_id == user_id).all()

def list_all_templates(db: Session):
    """Retrieves all templates in the system."""
    return db.query(CampaignTemplate).all()
