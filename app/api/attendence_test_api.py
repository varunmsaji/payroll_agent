from fastapi import APIRouter, HTTPException, Form
from datetime import datetime
from typing import Optional

from app.services.attendence_services import AttendanceService
from app.database.attendence import AttendanceEventDB, ShiftDB

router = APIRouter(
    prefix="/attendance",
    tags=["Attendance Test"],
)


# =========================================================
# MANUAL ATTENDANCE TEST ENDPOINT (TIME-INJECTED)
# =========================================================
@router.post("/manual")
def manual_attendance(
    employee_id: int = Form(...),
    action_time: str = Form(..., description="ISO datetime e.g. 2026-01-11T09:00:00"),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
):
    """
    TEST-ONLY ENDPOINT

    ✔ No datetime monkey-patching
    ✔ Uses injected time (production-safe pattern)
    ✔ Matches Face Attendance logic
    """

    # -----------------------------------------------------
    # 1️⃣ Parse injected time
    # -----------------------------------------------------
    try:
        now = datetime.fromisoformat(action_time)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid action_time format. Use ISO datetime.",
        )

    today = now.date()

    # -----------------------------------------------------
    # 2️⃣ Validate shift
    # -----------------------------------------------------
    shift = ShiftDB.get_employee_shift(employee_id, today)
    if not shift:
        raise HTTPException(
            status_code=400,
            detail="No active shift assigned to employee",
        )

    # -----------------------------------------------------
    # 3️⃣ Compute session window
    # -----------------------------------------------------
    window_start, window_end, _, _, _ = AttendanceService._get_shift_window(
        shift, today
    )

    # -----------------------------------------------------
    # 4️⃣ Fetch events ONLY up to injected time
    # -----------------------------------------------------
    events = AttendanceEventDB.get_events_for_window(
        employee_id,
        window_start,
        now,
    )

    meta = {
        "latitude": latitude,
        "longitude": longitude,
        "method": "manual-test",
        "forced_time": now.isoformat(),
    }

    # -----------------------------------------------------
    # 5️⃣ Decide action (same logic as Face API)
    # -----------------------------------------------------
    try:
        if not events:
            action = "check_in"
            result = AttendanceService.check_in(
                employee_id,
                source="manual-test",
                meta=meta,
                now=now,
            )

        else:
            last_event = events[-1]["event_type"]

            if last_event == "check_in":
                action = "break_start"
                result = AttendanceService.break_start(
                    employee_id,
                    source="manual-test",
                    meta=meta,
                    now=now,
                )

            elif last_event == "break_start":
                action = "break_end"
                result = AttendanceService.break_end(
                    employee_id,
                    source="manual-test",
                    meta=meta,
                    now=now,
                )

            else:
                action = "check_out"
                result = AttendanceService.check_out(
                    employee_id,
                    source="manual-test",
                    meta=meta,
                    now=now,
                )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # -----------------------------------------------------
    # 6️⃣ Response
    # -----------------------------------------------------
    return {
        "test_mode": True,
        "employee_id": employee_id,
        "action": action,
        "used_time": now.isoformat(),
        "attendance_event": result,
    }
