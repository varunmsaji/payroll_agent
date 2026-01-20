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
        print("\n================= PROCESS_PUNCH =================")
        print("employee_id:", employee_id)
        print("event_time :", event_time)
        print("meta       :", meta)

        meta = meta or {}
        dt = event_time.date()

        # -------------------------------------------------
        # Duplicate punch protection
        # -------------------------------------------------
        print("→ Checking duplicate punch")
        if AttendanceEventDB.exists_recent_event(
            employee_id=employee_id,
            event_time=event_time,
            seconds=30,
        ):
            print("⚠ DUPLICATE punch detected")
            return {"ignored": True, "reason": "duplicate_punch"}

        # -------------------------------------------------
        # Load policy (for late/OT etc.)
        # -------------------------------------------------
        policy = AttendancePolicyDB.get_policy_for_date(dt)
        print("→ Policy loaded:", policy)

        # -------------------------------------------------
        # Load shift (for break logic)
        # -------------------------------------------------
        shift = ShiftDB.get_employee_shift(employee_id, dt)
        print("→ Shift loaded:", shift)

        # -------------------------------------------------
        # Face confidence validation
        # -------------------------------------------------
        confidence = meta.get("confidence")
        print("→ Face confidence:", confidence)

        if confidence is not None:
            min_conf = getattr(policy, "min_face_confidence", None)
            print("→ Min required confidence:", min_conf)
            if min_conf and confidence < min_conf:
                print("❌ Face rejected")
                raise AttendanceRejected("Face confidence too low")

        # -------------------------------------------------
        # Fetch current session events
        # -------------------------------------------------
        print("→ Fetching session events")
        events = cls._get_session_events(employee_id, dt)

        print(f"→ Session events count: {len(events)}")
        for ev in events:
            print("   EVENT:", ev["event_type"], ev["event_time"])

        state = cls._derive_state(events)
        print("→ Derived state:", state)

        # -------------------------------------------------
        # Decide intent (FIXED LOGIC)
        # -------------------------------------------------
        if not state["checked_in"]:
            action = "check_in"

        elif state["on_break"]:
            action = "break_end"

        elif shift and shift.get("break_required"):
            action = "break_start"

        else:
            action = "check_out"

        print("→ Decided action:", action)

        # -------------------------------------------------
        # Insert semantic event
        # -------------------------------------------------
        print("→ Inserting event into DB")
        event = AttendanceEventDB.add_event(
            employee_id=employee_id,
            event_type=action,
            source=source,
            meta=meta,
            event_time=event_time,
        )
        print("✓ Event inserted:", event)

        # -------------------------------------------------
        # Recalculate attendance
        # -------------------------------------------------
        print("→ Recalculating attendance")
        cls.recalculate_for_date(employee_id, dt)
        print("✓ Recalculation done")

        print("================= END PROCESS_PUNCH =================\n")

        return {
            "action": action,
            "event": event,
        }


    # =========================================================
    # INTERNAL HELPERS
    # =========================================================
    @classmethod
    def _get_session_events(cls, employee_id, dt: date):
        print("→ _get_session_events()")

        shift = ShiftDB.get_employee_shift(employee_id, dt)
        print("  shift:", shift)

        window_start, window_end, *_ = cls._get_shift_window(shift, dt)
        print("  window_start:", window_start)
        print("  window_end  :", window_end)

        policy = AttendancePolicyDB.get_policy_for_date(dt)
        allowed_start = window_start - timedelta(
            minutes=policy.early_checkin_grace_minutes
        )

        extended_window_end = window_end + timedelta(hours=12)

        print("  allowed_start:", allowed_start)
        print("  extended_end :", extended_window_end)

        events = AttendanceEventDB.get_events_for_window(
            employee_id,
            allowed_start,
            extended_window_end,
        )

        return events

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
            print("❌ Payroll locked")
            raise AttendanceLocked("Attendance locked")

        shift = ShiftDB.get_employee_shift(employee_id, dt)
        print("  shift:", shift)

        window_start, window_end, required_hours, is_night, shift_id = cls._get_shift_window(
            shift, dt
        )

        extended_window_end = window_end + timedelta(hours=12)

        events = AttendanceEventDB.get_events_for_window(
            employee_id,
            window_start,
            extended_window_end,
        )

        print("  recalculation events:", len(events))
        for ev in events:
            print("    EVENT:", ev["event_type"], ev["event_time"])

        work_sec, break_sec, check_in, check_out = engine.compute_work_and_breaks(events)

        print("  work_sec :", work_sec)
        print("  break_sec:", break_sec)
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

        print("  RESULT → net:", net_hours,
              "late:", late_minutes,
              "early:", early_minutes,
              "ot:", overtime_minutes,
              "status:", status)

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
