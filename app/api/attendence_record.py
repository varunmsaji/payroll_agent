from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, date

from app.services.attendence.service import AttendanceService
from app.services.attendence.exceptions import (
    AlreadyCheckedIn,
    NoActiveCheckIn,
    BreakAlreadyRunning,
    NoActiveBreak,
    AttendanceLocked,
)

router = APIRouter(
    prefix="/attendance",
    tags=["Attendance"],
)

# -------------------------------------------------------------------
# ✅ TIME DEPENDENCY (FIXED)
# -------------------------------------------------------------------

def get_now(
    now: Optional[datetime] = Query(None),
) -> datetime:
    """
    Unified server time.
    - Uses ?now= (for tests)
    - Falls back to real UTC time (for prod)
    """
    if now:
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now
    return datetime.now(timezone.utc)

# -------------------------------------------------------------------
# ⚠️ TEMP EMPLOYEE DEPENDENCY
# -------------------------------------------------------------------

def get_current_employee_id() -> int:
    """
    Replace later with JWT / session logic
    """
    return 36

# -------------------------------------------------------------------
# RESPONSE SCHEMAS
# -------------------------------------------------------------------

class AttendanceActionResponse(BaseModel):
    success: bool
    event_type: str
    event_time: datetime
    message: Optional[str] = None


class AttendanceSummaryResponse(BaseModel):
    employee_id: int
    date: date
    status: str
    check_in: Optional[datetime]
    check_out: Optional[datetime]
    total_hours: float
    net_hours: float
    break_minutes: int
    late_minutes: int
    early_exit_minutes: int
    overtime_minutes: int
    is_late: bool
    is_overtime: bool
    is_weekend: bool
    is_holiday: bool
    is_night_shift: bool

# -------------------------------------------------------------------
# ACTION ENDPOINTS
# -------------------------------------------------------------------

@router.post("/check-in", response_model=AttendanceActionResponse)
def check_in(
    source: str = "api",
    employee_id: int = Depends(get_current_employee_id),
    now: datetime = Depends(get_now),  # ✅ FIXED
):
    try:
        ev = AttendanceService.check_in(
            employee_id=employee_id,
            source=source,
            now=now,
        )
        return AttendanceActionResponse(
            success=True,
            event_type="check_in",
            event_time=ev["event_time"],
            message="Checked in successfully",
        )

    except AlreadyCheckedIn:
        raise HTTPException(status_code=409, detail="Already checked in")

    except AttendanceLocked:
        raise HTTPException(status_code=423, detail="Attendance is locked")


@router.post("/check-out", response_model=AttendanceActionResponse)
def check_out(
    source: str = "api",
    employee_id: int = Depends(get_current_employee_id),
    now: datetime = Depends(get_now),  # ✅ FIXED
):
    try:
        ev = AttendanceService.check_out(
            employee_id=employee_id,
            source=source,
            now=now,
        )
        return AttendanceActionResponse(
            success=True,
            event_type="check_out",
            event_time=ev["event_time"],
            message="Checked out successfully",
        )

    except NoActiveCheckIn:
        raise HTTPException(status_code=400, detail="No active check-in")

    except AttendanceLocked:
        raise HTTPException(status_code=423, detail="Attendance is locked")


@router.post("/break/start", response_model=AttendanceActionResponse)
def break_start(
    source: str = "api",
    employee_id: int = Depends(get_current_employee_id),
    now: datetime = Depends(get_now),  # ✅ FIXED
):
    try:
        ev = AttendanceService.break_start(
            employee_id=employee_id,
            source=source,
            now=now,
        )
        return AttendanceActionResponse(
            success=True,
            event_type="break_start",
            event_time=ev["event_time"],
            message="Break started",
        )

    except BreakAlreadyRunning:
        raise HTTPException(status_code=409, detail="Break already running")

    except NoActiveCheckIn:
        raise HTTPException(status_code=400, detail="No active check-in")


@router.post("/break/end", response_model=AttendanceActionResponse)
def break_end(
    source: str = "api",
    employee_id: int = Depends(get_current_employee_id),
    now: datetime = Depends(get_now),  # ✅ FIXED
):
    try:
        ev = AttendanceService.break_end(
            employee_id=employee_id,
            source=source,
            now=now,
        )
        return AttendanceActionResponse(
            success=True,
            event_type="break_end",
            event_time=ev["event_time"],
            message="Break ended",
        )

    except NoActiveBreak:
        raise HTTPException(status_code=400, detail="No active break")

# -------------------------------------------------------------------
# READ ENDPOINT
# -------------------------------------------------------------------

@router.get(
    "/summary/{dt}",
    response_model=AttendanceSummaryResponse,
)
def get_attendance_summary(
    dt: date,
    employee_id: int = Depends(get_current_employee_id),
):
    record = AttendanceService.recalculate_for_date(employee_id, dt)

    if not record:
        raise HTTPException(status_code=404, detail="No attendance record")

    return AttendanceSummaryResponse(**record)
