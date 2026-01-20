from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any

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
    event_time: Optional[datetime] = Field(
        None, example="2026-01-20T09:01:12Z"
    )

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

    print("\n================= API /attendance/punch =================")
    print("RAW payload:", payload.dict())

    try:
        event_time = payload.event_time or datetime.utcnow()
        print("Resolved event_time:", event_time)

        meta = {
            "device_id": payload.device_id,
            "confidence": payload.confidence,
            "location": payload.location,
        }

        if payload.extra:
            meta.update(payload.extra)

        print("Meta passed to service:", meta)

        print("→ Calling AttendanceService.process_punch()")
        result = AttendanceService.process_punch(
            employee_id=payload.employee_id,
            event_time=event_time,
            source="biometric",
            meta=meta,
        )
        print("← Service returned:", result)

        # Duplicate / ignored punch
        if isinstance(result, dict) and result.get("ignored"):
            print("⚠ Punch ignored:", result.get("reason"))
            return PunchResponse(
                success=True,
                ignored=True,
                reason=result.get("reason"),
            )

        response = PunchResponse(
            success=True,
            action=result["action"],
            event=result["event"],
        )

        print("✓ API response:", response.dict())
        print("================= END API /attendance/punch =================\n")

        return response

    except AttendanceException as e:
        print("❌ AttendanceException:", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        print("🔥 UNHANDLED EXCEPTION IN API:", repr(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark attendance",
        )
