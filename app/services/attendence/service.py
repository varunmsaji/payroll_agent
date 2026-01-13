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

    # =====================================================
    # PUBLIC ACTIONS (TIME-INJECTED)
    # =====================================================
    @classmethod
    def check_in(cls, employee_id, source="manual", meta=None, now: Optional[datetime] = None):
        now = now or datetime.utcnow()
        cls._ensure_no_open_checkin(employee_id, now.date())

        event = AttendanceEventDB.add_event(
            employee_id, "check_in", source, meta, event_time=now
        )
        cls.recalculate_for_date(employee_id, now.date())
        return event

    @classmethod
    def check_out(cls, employee_id, source="manual", meta=None, now: Optional[datetime] = None):
        now = now or datetime.utcnow()
        cls._ensure_has_open_checkin(employee_id, now.date())

        event = AttendanceEventDB.add_event(
            employee_id, "check_out", source, meta, event_time=now
        )
        cls.recalculate_for_date(employee_id, now.date())
        return event

    @classmethod
    def break_start(cls, employee_id, source="manual", meta=None, now: Optional[datetime] = None):
        now = now or datetime.utcnow()
        cls._ensure_has_open_checkin(employee_id, now.date())
        cls._ensure_no_open_break(employee_id, now.date())

        event = AttendanceEventDB.add_event(
            employee_id, "break_start", source, meta, event_time=now
        )
        cls.recalculate_for_date(employee_id, now.date())
        return event

    @classmethod
    def break_end(cls, employee_id, source="manual", meta=None, now: Optional[datetime] = None):
        now = now or datetime.utcnow()
        cls._ensure_has_open_break(employee_id, now.date())

        event = AttendanceEventDB.add_event(
            employee_id, "break_end", source, meta, event_time=now
        )
        cls.recalculate_for_date(employee_id, now.date())
        return event

    # =====================================================
    # INTERNAL STATE HELPERS
    # =====================================================
    @classmethod
    def _get_session_events(cls, employee_id, dt: date):
        shift = ShiftDB.get_employee_shift(employee_id, dt)
        window_start, window_end, *_ = cls._get_shift_window(shift, dt)

        policy = AttendancePolicyDB.get_policy_for_date(dt)
        allowed_start = window_start - timedelta(
            minutes=policy.early_checkin_grace_minutes
        )

        return AttendanceEventDB.get_events_for_window(
            employee_id, allowed_start, window_end
        )

    @staticmethod
    def _derive_state(events: List[Dict[str, Any]]):
        state = {"checked_in": False, "on_break": False}
        for ev in events:
            if ev["event_type"] == "check_in":
                state["checked_in"] = True
            elif ev["event_type"] == "check_out":
                state["checked_in"] = False
                state["on_break"] = False
            elif ev["event_type"] == "break_start":
                state["on_break"] = True
            elif ev["event_type"] == "break_end":
                state["on_break"] = False
        return state

    @classmethod
    def _ensure_no_open_checkin(cls, employee_id, dt):
        if cls._derive_state(cls._get_session_events(employee_id, dt))["checked_in"]:
            raise AlreadyCheckedIn("Employee already checked in")

    @classmethod
    def _ensure_has_open_checkin(cls, employee_id, dt):
        if not cls._derive_state(cls._get_session_events(employee_id, dt))["checked_in"]:
            raise NoActiveCheckIn("No active check-in")

    @classmethod
    def _ensure_no_open_break(cls, employee_id, dt):
        if cls._derive_state(cls._get_session_events(employee_id, dt))["on_break"]:
            raise BreakAlreadyRunning("Break already running")

    @classmethod
    def _ensure_has_open_break(cls, employee_id, dt):
        if not cls._derive_state(cls._get_session_events(employee_id, dt))["on_break"]:
            raise NoActiveBreak("No active break")

    # =====================================================
    # CORE RECALCULATION LOGIC
    # =====================================================
    @classmethod
    def recalculate_for_date(cls, employee_id, dt: date):
        policy = AttendancePolicyDB.get_policy_for_date(dt)
        engine = AttendanceEngine(policy)

        # 1️⃣ Payroll lock check
        existing = AttendanceDB.get_by_employee_and_date(employee_id, dt)
        if existing and existing.get("is_payroll_locked"):
            raise AttendanceLocked("Attendance locked")

        # 2️⃣ Day flags
        is_weekend = dt.weekday() >= 5
        is_holiday = HolidayDB.is_holiday(dt)
        has_leave = LeaveRequestDB.has_approved_leave(employee_id, dt)

        # 3️⃣ Shift + window
        shift = ShiftDB.get_employee_shift(employee_id, dt)
        window_start, window_end, required_hours, is_night, shift_id = cls._get_shift_window(
            shift, dt
        )

        # 4️⃣ Events
        events = AttendanceEventDB.get_events_for_window(
            employee_id, window_start, window_end
        )

        # 5️⃣ No events
        if not events:
            status = (
                "holiday" if is_holiday else
                "on_leave" if has_leave else
                "week_off" if is_weekend else
                "absent"
            )

            return AttendanceDB.upsert_full_attendance({
                "employee_id": employee_id,
                "shift_id": shift_id,
                "date": dt,
                "status": status,
                "is_weekend": is_weekend,
                "is_holiday": is_holiday,
                "is_night_shift": is_night,
            })

        # 6️⃣ Work & break
        work_sec, break_sec, check_in, check_out = engine.compute_work_and_breaks(events, shift, dt)

        total_hours = round((work_sec + break_sec) / 3600, 2)
        net_hours = round(work_sec / 3600, 2)

        # 7️⃣ Late / early / OT
        late_minutes, is_late = engine.compute_late(shift, dt, check_in)
        early_minutes, is_early_checkout = engine.compute_early(shift, dt, check_out)
        overtime_minutes, is_overtime = engine.compute_overtime(
            check_out, window_end, late_minutes
        )

        # 8️⃣ Break policy enforcement
        break_violation = False
        break_taken = False

        if shift and shift.get("break_start") and shift.get("break_end"):
            break_start_dt = datetime.combine(dt, shift["break_start"])
            break_end_dt = datetime.combine(dt, shift["break_end"])
            grace = shift.get("break_grace_minutes", 0)
            allowed_break_end = break_end_dt + timedelta(minutes=grace)

            for ev in events:
                if ev["event_type"] == "break_start":
                    break_taken = True
                    if not (break_start_dt <= ev["event_time"] <= break_end_dt):
                        break_violation = True

                elif ev["event_type"] == "break_end":
                    if ev["event_time"] > allowed_break_end:
                        break_violation = True

            if shift.get("break_required", True) and not break_taken:
                break_violation = True

        # 9️⃣ Status decision
        status = engine.decide_status(net_hours, required_hours)
        if break_violation:
            status = shift.get("break_violation_action", "short_hours")

        # 🔟 Persist
        return AttendanceDB.upsert_full_attendance({
            "employee_id": employee_id,
            "shift_id": shift_id,
            "date": dt,
            "check_in": check_in,
            "check_out": check_out,
            "total_hours": total_hours,
            "net_hours": net_hours,
            "break_minutes": int(break_sec / 60),
            "late_minutes": late_minutes,
            "early_exit_minutes": early_minutes,
            "overtime_minutes": overtime_minutes,
            "is_late": is_late,
            "is_early_checkout": is_early_checkout,
            "is_overtime": is_overtime,
            "is_weekend": is_weekend,
            "is_holiday": is_holiday,
            "is_night_shift": is_night,
            "status": status,
            "is_payroll_locked": False,
            "locked_at": None,
        })

    # =====================================================
    # SHIFT WINDOW
    # =====================================================
    @classmethod
    def _get_shift_window(cls, shift, dt):
        """
        Returns:
        (window_start, window_end, required_hours, is_night, shift_id)
        """

        # -----------------------------
        # No shift assigned
        # -----------------------------
        if not shift:
            return (
                datetime.combine(dt, time(0, 0)),
                datetime.combine(dt, time(23, 59)),
                8.0,          # default required hours
                False,
                None,
            )

        start = shift["start_time"]
        end = shift["end_time"]
        is_night = shift.get("is_night_shift", False)
        required_hours = float(shift.get("required_hours", 8.0))

        # -----------------------------
        # Night / cross-day shift
        # -----------------------------
        if is_night or end <= start:
            return (
                datetime.combine(dt, start),
                datetime.combine(dt + timedelta(days=1), end),
                required_hours,
                True,
                shift["shift_id"],
            )

        # -----------------------------
        # Normal day shift
        # -----------------------------
        return (
            datetime.combine(dt, start),
            datetime.combine(dt, end),
            required_hours,
            False,
            shift["shift_id"],
        )
