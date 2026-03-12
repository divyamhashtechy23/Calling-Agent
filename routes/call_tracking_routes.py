"""
Call Tracking Routes — GET API for [Salesy].[dbo].[AiCallTracking].

Endpoints:
    GET  /api/call-tracking            → paginated list of all records
    GET  /api/call-tracking/{call_id}  → single record by call_id
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas import AiCallTrackingResponse, AiCallTrackingListResponse
from services.call_tracking_service import CallTrackingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/call-tracking", tags=["Call Tracking"])

# Singleton service instance
_service = CallTrackingService()


# ── List all records (paginated) ─────────────────────────────────── #

@router.get(
    "",
    summary="List AiCallTracking records",
    description=(
        "Returns a paginated list of call-tracking records from SQL Server. "
        "Supports filtering by org_id and final_status."
    ),
)
def list_call_tracking(
    limit: int = Query(50, ge=1, le=200, description="Records per page (max 200)"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    org_id: Optional[str] = Query(None, description="Filter by organization ID"),
    final_status: Optional[str] = Query(None, description="Filter by final call status"),
):
    """Fetch paginated AiCallTracking records with optional filters."""
    try:
        result = _service.get_all(
            limit=limit,
            offset=offset,
            org_id=org_id,
            final_status=final_status,
        )

        # Convert ORM objects → Pydantic models
        records = [
            AiCallTrackingResponse.model_validate(r)
            for r in result["records"]
        ]

        # Build response schema and explicitly dump to JSON-compatible dict to bypass FastAPI encoder crash
        response = AiCallTrackingListResponse(
            total_count=result["total_count"],
            limit=result["limit"],
            offset=result["offset"],
            records=records,
        )
        return response.model_dump(mode="json")

    except RuntimeError as exc:
        # Connection string not configured
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("list_call_tracking failed: %s", exc, exc_info=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch call-tracking records",
        )


# ── Single record by call_id ────────────────────────────────────── #

@router.get(
    "/{call_id}",
    response_model=AiCallTrackingResponse,
    summary="Get a single AiCallTracking record",
    description="Returns a single call-tracking record identified by its call_id.",
)
def get_call_tracking(call_id: str):
    """Fetch one AiCallTracking record by call_id."""
    try:
        record = _service.get_by_call_id(call_id)
        if record is None:
            raise HTTPException(
                status_code=404,
                detail=f"No AiCallTracking record found for call_id: {call_id}",
            )
        return AiCallTrackingResponse.model_validate(record)

    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("get_call_tracking failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch call-tracking record",
        )
