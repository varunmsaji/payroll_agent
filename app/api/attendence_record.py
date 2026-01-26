from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.attendence import AttendanceService
from app.services.attendence.exceptions import AttendanceException

router = APIRouter(
    prefix="/attendance",
    tags=["Attendance (Biometric / Face)"],
)


# =========================================================
# REQUEST SCHEMA
# =========================================================
class PunchRequest(BaseModel):
    employee_id: int = Field(..., example=101)
    event_time: Optional[datetime] = Field(None, example="2026-01-20T09:01:12Z")

    # Metadata from device
    device_id: Optional[str] = Field(None, example="FACE-01")
    confidence: Optional[float] = Field(None, example=0.93)
    location: Optional[str] = Field(None, example="Main Gate")
    extra: Optional[Dict[str, Any]] = None


# =========================================================
# RESPONSE SCHEMA
# =========================================================
class PunchResponse(BaseModel):
    success: bool
    action: Optional[str]
    event: Optional[Dict[str, Any]]
    ignored: Optional[bool] = False
    reason: Optional[str] = None


# =========================================================
# BIOMETRIC / FACE PUNCH ENDPOINT
# =========================================================
@router.post(
    "/punch",
    response_model=PunchResponse,
    status_code=status.HTTP_200_OK,
)
def mark_attendance(payload: PunchRequest):
    """
    BIOMETRIC / FACE SCANNER ENTRY POINT
    """

    try:
        event_time = payload.event_time or datetime.utcnow()

        meta = {
            "device_id": payload.device_id,
            "confidence": payload.confidence,
            "location": payload.location,
        }

        if payload.extra:
            meta.update(payload.extra)

        result = AttendanceService.process_punch(
            employee_id=payload.employee_id,
            event_time=event_time,
            source="biometric",
            meta=meta,
        )

        # Duplicate / ignored punch
        if isinstance(result, dict) and result.get("ignored"):
            return PunchResponse(
                success=True,
                ignored=True,
                reason=result.get("reason"),
            )

        return PunchResponse(
            success=True,
            action=result["action"],
            event=result["event"],
        )

    except AttendanceException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark attendance",
        )
