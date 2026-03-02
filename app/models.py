"""
Database Models — SQLAlchemy ORM definitions.

WHAT CHANGED:
    - 'retell_call_id' → 'bolna_execution_id'
      Bolna calls a "call" an "execution" — each call gets an execution_id.
      This is the unique identifier that links our DB record to Bolna's data.

    Everything else stays the same — the Call model is generic enough
    to work with any calling provider.
"""

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
    bolna_execution_id = Column(String, nullable=True, index=True)   # was: retell_call_id
    status = Column(String, default="queued")
    transcript = Column(Text, nullable=True)
    call_summary = Column(Text, nullable=True)          # from Bolna completed webhook
    recording_url = Column(String, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    interest_level = Column(String, nullable=True)
    callback_requested = Column(Boolean, default=False)
    callback_time = Column(String, nullable=True)
    stop_sequence = Column(Boolean, default=False)