from fastapi import APIRouter, HTTPException, Form
from datetime import datetime
from typing import Optional
import logging

from app.services.attendence import AttendanceService
from app.database.attendence import AttendanceEventDB, ShiftDB

logger = logging.getLogger("attendance.manual")

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
    logger.info("==== MANUAL ATTENDANCE START ====")

    # 1️⃣ Parse time
    try:
        now = datetime.fromisoformat(action_time)
    except ValueError:
        raise HTTPException(400, "Invalid action_time format")

    today = now.date()

    # 2️⃣ Validate shift
    shift = ShiftDB.get_employee_shift(employee_id, today)
    if not shift:
        raise HTTPException(400, "No active shift assigned")

    meta = {
        "latitude": latitude,
        "longitude": longitude,
        "method": "manual-test",
        "forced_time": now.isoformat(),
    }

    try:
        # 🔑 CRITICAL FIX: use SERVICE STATE, not API events
        events = AttendanceService._get_session_events(employee_id, today)
        state = AttendanceService._derive_state(events)

        logger.debug(f"Derived state: {state}")

        if not state["checked_in"]:
            action = "check_in"
            result = AttendanceService.check_in(
                employee_id, "manual-test", meta, now
            )

        elif state["checked_in"] and state["on_break"]:
            action = "break_end"
            result = AttendanceService.break_end(
                employee_id, "manual-test", meta, now
            )

        elif state["checked_in"] and not state["on_break"]:
            # decide break vs checkout
            window_start, window_end, *_ = AttendanceService._get_shift_window(
                shift, today
            )

            if now < window_end:
                action = "break_start"
                result = AttendanceService.break_start(
                    employee_id, "manual-test", meta, now
                )
            else:
                action = "check_out"
                result = AttendanceService.check_out(
                    employee_id, "manual-test", meta, now
                )

    except Exception as e:
        logger.exception("Attendance action failed")
        raise HTTPException(400, f"{type(e).__name__}: {str(e)}")

    logger.info(f"SUCCESS action={action}")
    logger.info("==== MANUAL ATTENDANCE END ====")

    return {
        "test_mode": True,
        "employee_id": employee_id,
        "action": action,
        "used_time": now.isoformat(),
        "attendance_event": result,
    }
