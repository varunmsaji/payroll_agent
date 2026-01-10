from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from typing import Dict, Any, List

from app.database.attendence import (
    AttendanceDB,
    AttendanceEventDB,
    HolidayDB,
    ShiftDB,
)
from app.database.connection import get_connection
from app.database.leave import LeaveDB
from app.services.attendance_engine import AttendanceEngine


# =========================================================
# BUSINESS EXCEPTIONS
# =========================================================
class AttendanceError(Exception):
    pass


class AlreadyCheckedIn(AttendanceError):
    pass


class NoActiveCheckIn(AttendanceError):
    pass


class BreakAlreadyRunning(AttendanceError):
    pass


class NoActiveBreak(AttendanceError):
    pass


class AttendanceLocked(AttendanceError):
    pass


# =========================================================
# POLICY MODEL
# =========================================================
@dataclass
class AttendancePolicy:
    late_grace_minutes: int
    early_exit_grace_minutes: int
    early_checkin_grace_minutes: int
    full_day_fraction: float
    half_day_fraction: float
    overtime_enabled: bool


# =========================================================
# POLICY LOADER
# =========================================================
class AttendancePolicyDB:
    DEFAULT_POLICY = AttendancePolicy(
        late_grace_minutes=10,
        early_exit_grace_minutes=10,
        early_checkin_grace_minutes=0,
        full_day_fraction=0.75,
        half_day_fraction=0.5,
        overtime_enabled=True,
    )

    @staticmethod
    def get_policy_for_date(dt: date) -> AttendancePolicy:
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()

            end_of_day = datetime.combine(dt, time(23, 59, 59))

            cur.execute(
                """
                SELECT
                    late_grace_minutes,
                    early_exit_grace_minutes,
                    early_checkin_grace_minutes,
                    full_day_fraction,
                    half_day_fraction,
                    overtime_enabled
                FROM attendance_policies
                WHERE created_at <= %s
                ORDER BY created_at DESC
                LIMIT 1;
                """,
                (end_of_day,),
            )

            row = cur.fetchone()
            cur.close()

            if not row:
                return AttendancePolicyDB.DEFAULT_POLICY

            return AttendancePolicy(
                late_grace_minutes=row[0],
                early_exit_grace_minutes=row[1],
                early_checkin_grace_minutes=row[2],
                full_day_fraction=row[3],
                half_day_fraction=row[4],
                overtime_enabled=row[5],
            )

        except Exception:
            return AttendancePolicyDB.DEFAULT_POLICY

        finally:
            if conn:
                conn.close()


# =========================================================
# ATTENDANCE SERVICE
# =========================================================
class AttendanceService:

    # =====================================================
    # PUBLIC ACTIONS
    # =====================================================
    @classmethod
    def check_in(cls, employee_id: int, source="manual", meta=None):
        today = datetime.now().date()
        cls._ensure_no_open_checkin(employee_id, today)

        event = AttendanceEventDB.add_event(employee_id, "check_in", source, meta)
        cls.recalculate_for_date(employee_id, today)
        return event

    @classmethod
    def check_out(cls, employee_id: int, source="manual", meta=None):
        today = datetime.now().date()
        cls._ensure_has_open_checkin(employee_id, today)

        event = AttendanceEventDB.add_event(employee_id, "check_out", source, meta)
        cls.recalculate_for_date(employee_id, today)
        return event

    @classmethod
    def break_start(cls, employee_id: int, source="manual", meta=None):
        today = datetime.now().date()
        cls._ensure_has_open_checkin(employee_id, today)
        cls._ensure_no_open_break(employee_id, today)

        event = AttendanceEventDB.add_event(employee_id, "break_start", source, meta)
        cls.recalculate_for_date(employee_id, today)
        return event

    @classmethod
    def break_end(cls, employee_id: int, source="manual", meta=None):
        today = datetime.now().date()
        cls._ensure_has_open_break(employee_id, today)

        event = AttendanceEventDB.add_event(employee_id, "break_end", source, meta)
        cls.recalculate_for_date(employee_id, today)
        return event

    # =====================================================
    # SESSION-AWARE VALIDATION HELPERS
    # =====================================================
    @classmethod
    def _get_session_events(cls, employee_id: int, dt: date):
        shift = ShiftDB.get_employee_shift(employee_id, dt)
        window_start, window_end, _, _, _ = cls._get_shift_window(shift, dt)

        policy = AttendancePolicyDB.get_policy_for_date(dt)
        allowed_start = window_start - timedelta(
            minutes=policy.early_checkin_grace_minutes
        )

        return AttendanceEventDB.get_events_for_window(
            employee_id,
            allowed_start,
            window_end,
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
    def _ensure_no_open_checkin(cls, employee_id: int, dt: date):
        if cls._derive_state(cls._get_session_events(employee_id, dt))["checked_in"]:
            raise AlreadyCheckedIn("Employee already checked in for this session.")

    @classmethod
    def _ensure_has_open_checkin(cls, employee_id: int, dt: date):
        if not cls._derive_state(cls._get_session_events(employee_id, dt))["checked_in"]:
            raise NoActiveCheckIn("No active check-in for this session.")

    @classmethod
    def _ensure_no_open_break(cls, employee_id: int, dt: date):
        if cls._derive_state(cls._get_session_events(employee_id, dt))["on_break"]:
            raise BreakAlreadyRunning("Break already running.")

    @classmethod
    def _ensure_has_open_break(cls, employee_id: int, dt: date):
        if not cls._derive_state(cls._get_session_events(employee_id, dt))["on_break"]:
            raise NoActiveBreak("No active break to end.")

    # =====================================================
    # PAYROLL RECALCULATION (CRITICAL FIX APPLIED)
    # =====================================================
    @classmethod
    def recalculate_for_date(cls, employee_id: int, dt: date):
        policy = AttendancePolicyDB.get_policy_for_date(dt)
        engine = AttendanceEngine(policy)

        existing = AttendanceDB.get_by_employee_and_date(employee_id, dt)
        if existing and existing.get("is_payroll_locked"):
            raise AttendanceLocked("Attendance locked for payroll.")

        is_weekend = dt.weekday() >= 5
        is_holiday = HolidayDB.is_holiday(dt)
        has_leave = LeaveDB.has_approved_leave(employee_id, dt)

        shift = ShiftDB.get_employee_shift(employee_id, dt)
        window_start, window_end, required_hours, is_night_shift, shift_id = cls._get_shift_window(shift, dt)

        allowed_start = window_start - timedelta(
            minutes=policy.early_checkin_grace_minutes
        )

        events = AttendanceEventDB.get_events_for_window(
            employee_id,
            allowed_start,
            window_end,
        )

        if not events:
            status = (
                "holiday" if is_holiday
                else "on_leave" if has_leave
                else "week_off" if is_weekend
                else "absent"
            )

            return AttendanceDB.upsert_full_attendance({
                "employee_id": employee_id,
                "shift_id": shift_id,
                "date": dt,
                "check_in": None,
                "check_out": None,
                "total_hours": 0.0,
                "net_hours": 0.0,
                "break_minutes": 0,
                "overtime_minutes": 0,
                "late_minutes": 0,
                "early_exit_minutes": 0,
                "is_late": False,
                "is_early_checkout": False,
                "is_overtime": False,
                "is_weekend": is_weekend,
                "is_holiday": is_holiday,
                "is_night_shift": is_night_shift,
                "status": status,
                "is_payroll_locked": False,
                "locked_at": None,
            })

        work_sec, break_sec, check_in, check_out = engine.compute_work_and_breaks(events)

        total_span = (check_out - check_in).total_seconds() if check_in and check_out else 0
        total_hours = round(total_span / 3600, 2)
        net_hours = round(work_sec / 3600, 2)
        break_minutes = int(break_sec / 60)

        late_minutes, is_late = engine.compute_late(shift, dt, check_in)
        early_minutes, _ = engine.compute_early(shift, dt, check_out)

        shift_end = None
        if shift:
            end = shift["end_time"]
            is_night = shift.get("is_night_shift", False)
            shift_end = (
                datetime.combine(dt + timedelta(days=1), end)
                if is_night or end <= shift["start_time"]
                else datetime.combine(dt, end)
            )

        overtime_minutes, is_overtime = engine.compute_overtime(
            check_out, shift_end, late_minutes
        )

        status = engine.decide_status(net_hours, required_hours)

        return AttendanceDB.upsert_full_attendance({
            "employee_id": employee_id,
            "shift_id": shift_id,
            "date": dt,
            "check_in": check_in,
            "check_out": check_out,
            "total_hours": total_hours,
            "net_hours": net_hours,
            "break_minutes": break_minutes,
            "overtime_minutes": overtime_minutes,
            "late_minutes": late_minutes,
            "early_exit_minutes": early_minutes,
            "is_late": is_late,
            "is_early_checkout": early_minutes > 0,
            "is_overtime": is_overtime,
            "is_weekend": is_weekend,
            "is_holiday": is_holiday,
            "is_night_shift": is_night_shift,
            "status": status,
            "is_payroll_locked": False,
            "locked_at": None,
        })

    # =====================================================
    # SHIFT WINDOW
    # =====================================================
    @classmethod
    def _get_shift_window(cls, shift, dt):
        if shift:
            start = shift["start_time"]
            end = shift["end_time"]
            is_night = shift.get("is_night_shift", False)
            shift_id = shift["shift_id"]

            if is_night or end <= start:
                window_start = datetime.combine(dt, start)
                window_end = datetime.combine(dt + timedelta(days=1), end)
            else:
                window_start = datetime.combine(dt, start)
                window_end = datetime.combine(dt, end)

            required_hours = round((window_end - window_start).total_seconds() / 3600, 2)
        else:
            shift_id = None
            is_night = False
            window_start = datetime.combine(dt, time(0, 0))
            window_end = datetime.combine(dt, time(23, 59))
            required_hours = 8.0

        return window_start, window_end, required_hours, is_night, shift_id
