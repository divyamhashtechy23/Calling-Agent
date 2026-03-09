"""
CallTrackingService — Query layer for [Salesy].[dbo].[AiCallTracking].

Reads call-tracking records from SQL Server.  All methods are
synchronous since we use plain SQLAlchemy sessions.
"""

import logging
from typing import Optional, List

from sqlalchemy import func
from app.mssql_database import get_mssql_session
from app.ai_call_tracking import AiCallTracking

logger = logging.getLogger(__name__)


class CallTrackingService:
    """Service for querying AiCallTracking records from SQL Server."""

    # ── List (paginated + filtered) ───────────────────────────────── #

    def get_all(
        self,
        limit: int = 50,
        offset: int = 0,
        org_id: Optional[str] = None,
        final_status: Optional[str] = None,
    ) -> dict:
        """
        Return a paginated list of AiCallTracking records.

        Args:
            limit:        Max records per page (capped at 200)
            offset:       Number of records to skip
            org_id:       Optional filter by organization
            final_status: Optional filter by call final status

        Returns:
            dict with total_count, limit, offset, records
        """
        session = get_mssql_session()
        try:
            query = session.query(AiCallTracking)

            # Apply optional filters
            if org_id:
                query = query.filter(AiCallTracking.org_id == org_id)
            if final_status:
                query = query.filter(AiCallTracking.final_status == final_status)

            # Total count (before pagination)
            total_count = query.count()

            # Order by created_at descending (newest first), then paginate
            records = (
                query
                .order_by(AiCallTracking.created_at.desc())
                .offset(offset)
                .limit(min(limit, 200))
                .all()
            )

            logger.info(
                "Fetched %d / %d AiCallTracking records (offset=%d)",
                len(records), total_count, offset,
            )

            return {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "records": records,
            }

        except Exception as exc:
            logger.error("Error querying AiCallTracking: %s", exc, exc_info=True)
            raise
        finally:
            session.close()

    # ── Single record by call_id ──────────────────────────────────── #

    def get_by_call_id(self, call_id: str) -> Optional[AiCallTracking]:
        """
        Fetch a single AiCallTracking record by its call_id.

        Returns:
            The AiCallTracking row or None if not found.
        """
        session = get_mssql_session()
        try:
            record = (
                session
                .query(AiCallTracking)
                .filter(AiCallTracking.call_id == call_id)
                .first()
            )
            return record

        except Exception as exc:
            logger.error(
                "Error fetching AiCallTracking call_id=%s: %s",
                call_id, exc, exc_info=True,
            )
            raise
        finally:
            session.close()
