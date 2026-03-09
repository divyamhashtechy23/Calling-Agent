"""
AiCallTracking ORM Model — maps to [Salesy].[dbo].[AiCallTracking] on SQL Server.

This is a READ-ONLY model used by the GET API to query call-tracking
records.  All 28 columns from the table are mapped here.
"""

from sqlalchemy import Column, String, Text, DateTime, Integer, Float, Boolean
from app.mssql_database import MssqlBase


class AiCallTracking(MssqlBase):
    __tablename__ = "AiCallTracking"
    __table_args__ = {"schema": "dbo"}

    call_id = Column(String, primary_key=True)
    start_status = Column(String, nullable=True)
    org_id = Column(String, nullable=True)
    sequence_id = Column(String, nullable=True)
    lead_id = Column(String, nullable=True)
    start_timestamp = Column(DateTime, nullable=True)
    final_status = Column(String, nullable=True)
    event_type = Column(String, nullable=True)
    initiated_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    total_cost = Column(Float, nullable=True)
    interest_level = Column(String, nullable=True)
    callback_requested = Column(Boolean, nullable=True)
    callback_time = Column(String, nullable=True)
    stop_sequence = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    recording_url = Column(String, nullable=True)
    provider_name = Column(String, nullable=True)
    telephony_provider = Column(String, nullable=True)
    agent_id = Column(String, nullable=True)
    provider_call_id = Column(String, nullable=True)
    hangup_reason = Column(String, nullable=True)
    raw_webhook_json = Column(Text, nullable=True)
    webhook_received_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
