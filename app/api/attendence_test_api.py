from fastapi import APIRouter, HTTPException, Form
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

from app.services.attendence_services import AttendanceService
from app.database.attendence import AttendanceEventDB, ShiftDB


router = APIRouter(
    prefix="/attendance",
    tags=["Attendance Test"],
)


# =========================================================
# TEST-ONLY TIME OVERRIDE (TEMPORARY)
# =========================================================
@contextmanager
def override_now(fake_now: datetime):
    """
    TEST ONLY.
    Temporarily overrides datetime.now() so AttendanceService
    behaves as if current time == fake_now.
    """
    real_now = datetime.now
    datetime.now = lambda: fake_now
    try:
        yield
    finally:
        datetime.now = real_now


# =========================================================
# MANUAL ATTENDANCE TEST ENDPOINT
# =========================================================
@router.post("/manual")
def manual_attendance(
    employee_id: int = Form(...),
    action_time: str = Form(..., description="ISO datetime e.g. 2026-01-11T09:00:00"),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
):
    """
    TEMPORARY TEST ENDPOINT

    Allows testing attendance flow without:
    - face recognition
    - waiting for real time
    """

    # Parse fake time
    try:
        fake_now = datetime.fromisoformat(action_time)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid action_time format. Use ISO datetime.",
        )

    today = fake_now.date()

    # Ensure employee has a shift
    shift = ShiftDB.get_employee_shift(employee_id, today)
    if not shift:
        raise HTTPException(
            status_code=400,
            detail="No active shift assigned to employee",
        )

    # Compute shift window
    window_start, window_end, _, _, _ = AttendanceService._get_shift_window(
        shift, today
    )

    # Fetch session events up to fake time
    events = AttendanceEventDB.get_events_for_window(
        employee_id,
        window_start,
        fake_now,
    )

    meta = {
        "latitude": latitude,
        "longitude": longitude,
        "method": "manual-test",
        "forced_time": fake_now.isoformat(),
    }

    # Execute attendance logic with fake time
    try:
        with override_now(fake_now):

            if not events:
                action = "check_in"
                result = AttendanceService.check_in(
                    employee_id,
                    source="manual-test",
                    meta=meta,
                )

            else:
                last_event = events[-1]["event_type"]

                if last_event == "check_in":
                    action = "break_start"
                    result = AttendanceService.break_start(
                        employee_id,
                        source="manual-test",
                        meta=meta,
                    )

                elif last_event == "break_start":
                    action = "break_end"
                    result = AttendanceService.break_end(
                        employee_id,
                        source="manual-test",
                        meta=meta,
                    )

                else:
                    action = "check_out"
                    result = AttendanceService.check_out(
                        employee_id,
                        source="manual-test",
                        meta=meta,
                    )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "test_mode": True,
        "employee_id": employee_id,
        "action": action,
        "used_time": fake_now.isoformat(),
        "attendance_event": result,
    }
