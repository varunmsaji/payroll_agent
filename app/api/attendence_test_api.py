from fastapi import APIRouter, HTTPException, Form
from datetime import datetime
from typing import Optional

from app.services.attendence import AttendanceService
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

    ✔ Uses injected datetime
    ✔ Correctly decides check-in / break / check-out
    ✔ Fully compatible with AttendanceService + Payroll
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
    # 3️⃣ Compute shift window
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

    # -----------------------------------------------------
    # 5️⃣ Metadata
    # -----------------------------------------------------
    meta = {
        "latitude": latitude,
        "longitude": longitude,
        "method": "manual-test",
        "forced_time": now.isoformat(),
    }

    # -----------------------------------------------------
    # 6️⃣ Decide action (STATE + TIME AWARE ✅)
    # -----------------------------------------------------
    try:
        state = AttendanceService._derive_state(events)

        # ---------------------------------------------
        # NOT CHECKED IN → CHECK IN
        # ---------------------------------------------
        if not state["checked_in"]:
            action = "check_in"
            result = AttendanceService.check_in(
                employee_id,
                source="manual-test",
                meta=meta,
                now=now,
            )

        # ---------------------------------------------
        # ON BREAK → BREAK END
        # ---------------------------------------------
        elif state["checked_in"] and state["on_break"]:
            action = "break_end"
            result = AttendanceService.break_end(
                employee_id,
                source="manual-test",
                meta=meta,
                now=now,
            )

        # ---------------------------------------------
        # CHECKED IN, NOT ON BREAK
        # Decide break_start vs check_out
        # ---------------------------------------------
        elif state["checked_in"] and not state["on_break"]:
            if now < window_end:
                action = "break_start"
                result = AttendanceService.break_start(
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

        else:
            raise HTTPException(status_code=400, detail="Invalid attendance state")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # -----------------------------------------------------
    # 7️⃣ Response
    # -----------------------------------------------------
    return {
        "test_mode": True,
        "employee_id": employee_id,
        "action": action,
        "used_time": now.isoformat(),
        "attendance_event": result,
    }
