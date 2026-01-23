from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Optional

from app.database.attendence import (
    AttendanceDB,
    AttendanceEventDB,
    HolidayDB,
    ShiftDB,
)
from app.database.leave_database import LeaveRequestDB

from .engine import AttendanceEngine
from .policy import AttendancePolicyDB
from .exceptions import *
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from zoneinfo import ZoneInfo

from app.database.attendence import AttendanceEventDB, AttendanceDB, ShiftDB
from app.services.attendence.policy import AttendancePolicyDB
from app.services.attendence.exceptions import (
    AttendanceRejected,
    AttendanceException,
    EarlyPunchNotAllowed,
)

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")


class AttendanceService:

    # =========================================================
    # 🔥 ONLY ENTRY POINT (BIOMETRIC / FACE)
    # =========================================================
    
    @classmethod
    def process_punch(
        cls,
        employee_id: int,
        event_time: datetime,
        source: str = "biometric",
        meta: Optional[Dict[str, Any]] = None,
    ):
        meta = meta or {}

        # -------------------------------------------------
        # ✅ NORMALIZE EVENT TIME → UTC (MANDATORY)
        # -------------------------------------------------
        if event_time.tzinfo is None:
            raise AttendanceRejected("event_time must include timezone")

        event_time = event_time.astimezone(UTC)
        dt_local = event_time.astimezone(IST).date()

        # -------------------------------------------------
        # 🔁 DUPLICATE PUNCH PROTECTION (30s)
        # -------------------------------------------------
        if AttendanceEventDB.exists_recent_event(
            employee_id=employee_id,
            event_time=event_time,
            seconds=30,
        ):
            return {"ignored": True, "reason": "duplicate_punch"}

        # -------------------------------------------------
        # 📄 LOAD POLICY & SHIFT (LOCAL DATE)
        # -------------------------------------------------
        policy = AttendancePolicyDB.get_policy_for_date(dt_local)
        shift = ShiftDB.get_employee_shift(employee_id, dt_local)

        # -------------------------------------------------
        # 📊 FETCH SESSION EVENTS
        # -------------------------------------------------
        events = cls._get_session_events(employee_id, dt_local)
        state = cls._derive_state(events)

        # -------------------------------------------------
        # 🕘 COMPUTE SHIFT WINDOW (IST → UTC)
        # -------------------------------------------------
        if shift:
            shift_start_local = datetime.combine(dt_local, shift["start_time"])
            shift_start = shift_start_local.replace(tzinfo=IST).astimezone(UTC)

            shift_end_local = datetime.combine(dt_local, shift["end_time"])
            shift_end = shift_end_local.replace(tzinfo=IST).astimezone(UTC)

            # Night shift handling
            if shift_end <= shift_start:
                shift_end += timedelta(days=1)

            # -------------------------------------------------
            # ⛔ EARLY CHECK-IN BLOCK
            # -------------------------------------------------
            early_grace = int(policy.early_checkin_grace_minutes or 0)
            earliest_allowed = shift_start - timedelta(minutes=early_grace)

            if event_time < earliest_allowed:
                raise EarlyPunchNotAllowed(
                    f"Early check-in not allowed before "
                    f"{earliest_allowed.astimezone(IST).strftime('%H:%M')}"
                )

            # -------------------------------------------------
            # ⛔ LATE CHECK-IN BLOCK (BEYOND GRACE)
            # -------------------------------------------------
            late_grace = int(shift.get("late_grace_minutes", 0))
            latest_allowed = shift_start + timedelta(minutes=late_grace)

            if not state["checked_in"] and event_time > latest_allowed:
                raise AttendanceRejected(
                    f"Late check-in not allowed after "
                    f"{latest_allowed.astimezone(IST).strftime('%H:%M')}"
                )

            # -------------------------------------------------
            # ⛔ CHECK-IN AFTER SHIFT END
            # -------------------------------------------------
            if not state["checked_in"] and event_time > shift_end:
                raise AttendanceRejected(
                    f"Check-in not allowed after shift end "
                    f"({shift_end.astimezone(IST).strftime('%H:%M')})"
                )

        # -------------------------------------------------
        # 🧠 FACE CONFIDENCE VALIDATION
        # -------------------------------------------------
        confidence = meta.get("confidence")
        min_conf = getattr(policy, "min_face_confidence", None)

        if min_conf and confidence is not None and confidence < min_conf:
            raise AttendanceRejected("Face confidence too low")

        # -------------------------------------------------
        # 🧠 DECIDE ACTION (STATE MACHINE)
        # -------------------------------------------------
        had_break = any(ev["event_type"] == "break_start" for ev in events)

        if not state["checked_in"]:
            action = "check_in"

        elif state["on_break"]:
            action = "break_end"

        elif shift and shift.get("break_required") and not had_break:
            action = "break_start"

        else:
            action = "check_out"

        # -------------------------------------------------
        # 📝 INSERT EVENT (UTC)
        # -------------------------------------------------
        event = AttendanceEventDB.add_event(
            employee_id=employee_id,
            event_type=action,
            source=source,
            meta=meta,
            event_time=event_time,
        )

        # -------------------------------------------------
        # 🔄 RECALCULATE ATTENDANCE (LOCAL DATE)
        # -------------------------------------------------
        cls.recalculate_for_date(employee_id, dt_local)

        return {
            "action": action,
            "event": event,
        }

            # =========================================================
    # INTERNAL HELPERS
    # =========================================================
    @classmethod
    def _get_session_events(cls, employee_id, dt: date):
        shift = ShiftDB.get_employee_shift(employee_id, dt)

        window_start_local, window_end_local, *_ = cls._get_shift_window(shift, dt)

        # ✅ Convert to UTC
        window_start = window_start_local.replace(tzinfo=IST).astimezone(UTC)
        window_end = window_end_local.replace(tzinfo=IST).astimezone(UTC)

        # ✅ Widen window (VERY IMPORTANT)
        allowed_start = window_start - timedelta(hours=12)
        extended_window_end = window_end + timedelta(hours=12)

        return AttendanceEventDB.get_events_for_window(
            employee_id,
            allowed_start,
            extended_window_end,
        )


    @staticmethod
    def _derive_state(events: List[Dict[str, Any]]):
        print("→ _derive_state()")

        state = {"checked_in": False, "on_break": False}

        for ev in events:
            et = ev["event_type"]
            print("  processing event:", et)

            if et == "check_in":
                state["checked_in"] = True
            elif et == "check_out":
                state["checked_in"] = False
                state["on_break"] = False
            elif et == "break_start":
                state["on_break"] = True
            elif et == "break_end":
                state["on_break"] = False

        return state

    # =========================================================
    # RECALCULATION
    # =========================================================
    @classmethod
    def recalculate_for_date(cls, employee_id, dt: date):
        print("\n→ recalculate_for_date() employee:", employee_id, "date:", dt)

        policy = AttendancePolicyDB.get_policy_for_date(dt)
        engine = AttendanceEngine(policy)

        existing = AttendanceDB.get_by_employee_and_date(employee_id, dt)
        print("  existing attendance:", existing)

        if existing and existing.get("is_payroll_locked"):
            raise AttendanceLocked("Attendance locked")

        shift = ShiftDB.get_employee_shift(employee_id, dt)
        print("  shift:", shift)

        # -------------------------------------------------
        # ✅ GET SHIFT WINDOW (LOCAL → UTC)
        # -------------------------------------------------
        window_start_local, window_end_local, required_hours, is_night, shift_id = (
            cls._get_shift_window(shift, dt)
        )

        # 🔥 FIX: convert shift window to UTC
        window_start = window_start_local.replace(tzinfo=IST).astimezone(UTC)
        window_end = window_end_local.replace(tzinfo=IST).astimezone(UTC)

        extended_window_end = window_end + timedelta(hours=12)

        # -------------------------------------------------
        # ✅ FETCH EVENTS (UTC SAFE)
        # -------------------------------------------------
        events = AttendanceEventDB.get_events_for_window(
            employee_id,
            window_start,
            extended_window_end,
        )

        print("  recalculation events:", len(events))
        for ev in events:
            print("    EVENT:", ev["event_type"], ev["event_time"])

        work_sec, break_sec, check_in, check_out = engine.compute_work_and_breaks(events)

        print("  check_in :", check_in)
        print("  check_out:", check_out)

        net_hours = round(work_sec / 3600, 2)

        late_minutes, is_late = engine.compute_late(shift, dt, check_in)
        early_minutes, is_early_checkout = engine.compute_early(shift, dt, check_out)

        overtime_minutes, is_overtime = engine.compute_overtime(
            check_out,
            window_end,
            late_minutes,
        )

        status = engine.decide_status(net_hours, required_hours)

        return AttendanceDB.upsert_full_attendance({
            "employee_id": employee_id,
            "shift_id": shift_id,
            "date": dt,
            "check_in": check_in,
            "check_out": check_out,
            "total_hours": round((work_sec + break_sec) / 3600, 2),
            "net_hours": net_hours,
            "break_minutes": int(break_sec / 60),
            "late_minutes": late_minutes,
            "early_exit_minutes": early_minutes,
            "is_early_checkout": is_early_checkout,
            "overtime_minutes": overtime_minutes,
            "is_late": is_late,
            "is_overtime": is_overtime,
            "is_weekend": dt.weekday() >= 5,
            "is_holiday": HolidayDB.is_holiday(dt),
            "is_night_shift": is_night,
            "status": status,
            "is_payroll_locked": False,
            "locked_at": None,
        })


    # =========================================================
    # SHIFT WINDOW
    # =========================================================
    @classmethod
    def _get_shift_window(cls, shift, dt):
        if not shift:
            return (
                datetime.combine(dt, time(0, 0)),
                datetime.combine(dt, time(23, 59)),
                8.0,
                False,
                None,
            )

        start, end = shift["start_time"], shift["end_time"]
        is_night = shift.get("is_night_shift", False)

        if is_night or end <= start:
            return (
                datetime.combine(dt, start),
                datetime.combine(dt + timedelta(days=1), end),
                8.0,
                True,
                shift["shift_id"],
            )

        return (
            datetime.combine(dt, start),
            datetime.combine(dt, end),
            round(
                (datetime.combine(dt, end) - datetime.combine(dt, start)).total_seconds() / 3600,
                2,
            ),
            False,
            shift["shift_id"],
        )
