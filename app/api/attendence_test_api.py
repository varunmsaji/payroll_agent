from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Form, HTTPException

from app.database.attendence import AttendanceEventDB, ShiftDB
from app.services.attendence import AttendanceService

router = APIRouter(
    prefix="/attendance",
    tags=["Attendance Test"],
)


@router.post("/manual")
def manual_attendance(
    employee_id: int = Form(...),
    action_time: str = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
):
    """
    TEST-ONLY MANUAL ATTENDANCE (STATE MACHINE BASED)

    ✔ Deterministic
    ✔ Test-safe
    ✔ Matches HRMS behavior
    """

    try:
        now = datetime.fromisoformat(action_time)
    except ValueError:
        raise HTTPException(400, "Invalid action_time")

    today = now.date()

    # Validate shift
    shift = ShiftDB.get_employee_shift(employee_id, today)
    if not shift:
        raise HTTPException(400, "No active shift assigned")

    # Fetch events till now
    window_start, _, _, _, _ = AttendanceService._get_shift_window(shift, today)
    events = AttendanceEventDB.get_events_for_window(
        employee_id,
        window_start,
        now,
    )

    state = AttendanceService._derive_state(events)

    # Has break ever started today?
    had_break = any(ev["event_type"] == "break_start" for ev in events)

    meta = {
        "latitude": latitude,
        "longitude": longitude,
        "method": "manual-test",
        "forced_time": now.isoformat(),
    }

    try:
        # ---------------------------------
        # CHECK IN
        # ---------------------------------
        if not state["checked_in"]:
            action = "check_in"
            result = AttendanceService.check_in(
                employee_id,
                meta=meta,
                source="manual-test",
                now=now,
            )

        # ---------------------------------
        # BREAK END
        # ---------------------------------
        elif state["on_break"]:
            action = "break_end"
            result = AttendanceService.break_end(
                employee_id,
                meta=meta,
                source="manual-test",
                now=now,
            )

        # ---------------------------------
        # BREAK START or CHECK OUT
        # ---------------------------------
        else:
            if not had_break:
                action = "break_start"
                result = AttendanceService.break_start(
                    employee_id,
                    meta=meta,
                    source="manual-test",
                    now=now,
                )
            else:
                action = "check_out"
                result = AttendanceService.check_out(
                    employee_id,
                    meta=meta,
                    source="manual-test",
                    now=now,
                )

    except Exception as e:
        raise HTTPException(400, str(e))

    return {
        "employee_id": employee_id,
        "action": action,
        "used_time": now.isoformat(),
        "event": result,
    }
