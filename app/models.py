from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime

Base = declarative_base()

class Call(Base):
    __tablename__ = "calls"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String)
    lead_name = Column(String)
    lead_phone = Column(String)
    retell_call_id = Column(String, nullable=True, index=True)
    status = Column(String, default="queued")
    transcript = Column(Text, nullable=True)
    call_summary = Column(Text, nullable=True)          # from Retell call_analyzed event
    recording_url = Column(String, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    interest_level = Column(String, nullable=True)
    callback_requested = Column(Boolean, default=False)
    callback_time = Column(String, nullable=True)
    stop_sequence = Column(Boolean, default=False)