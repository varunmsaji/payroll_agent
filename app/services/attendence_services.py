from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from typing import Dict, Any, Optional, List

from app.database.attendence import (
    AttendanceDB,
    AttendanceEventDB,
    HolidayDB,
    ShiftDB,
)
from app.database.connection import get_connection


# =========================================================
# BUSINESS EXCEPTIONS (cleaner API responses, not ValueError)
# =========================================================
class AttendanceError(Exception):
    """Base business exception for attendance domain."""


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
# POLICY MODEL (thread-safe, immutable per calculation)
# =========================================================
@dataclass
class AttendancePolicy:
    late_grace_minutes: int
    early_exit_grace_minutes: int
    full_day_fraction: float
    half_day_fraction: float
    overtime_enabled: bool


# =========================================================
# POLICY LOADER (supports history)
# =========================================================
class AttendancePolicyDB:
    DEFAULT_POLICY = AttendancePolicy(
        late_grace_minutes=10,
        early_exit_grace_minutes=10,
        full_day_fraction=0.75,
        half_day_fraction=0.5,
        overtime_enabled=True,
    )

    @staticmethod
    def get_policy_for_date(dt: date) -> AttendancePolicy:
        """
        Pick the policy that existed on this date.
        If nothing found → return safe, sensible defaults.
        """

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
                late_grace_minutes=int(row[0]),
                early_exit_grace_minutes=int(row[1]),
                full_day_fraction=float(row[2]),
                half_day_fraction=float(row[3]),
                overtime_enabled=bool(row[4]),
            )

        except Exception:
            return AttendancePolicyDB.DEFAULT_POLICY

        finally:
            if conn:
                conn.close()


# =========================================================
# SIMPLE LEAVE CHECK
# =========================================================
class LeaveDB:
    @staticmethod
    def has_approved_leave(employee_id: int, dt: date) -> bool:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT 1
            FROM leave_requests
            WHERE employee_id = %s
              AND status = 'approved'
              AND start_date <= %s
              AND end_date >= %s
            LIMIT 1;
            """,
            (employee_id, dt, dt),
        )

        row = cur.fetchone()
        cur.close()
        conn.close()
        return row is not None


# =========================================================
# PURE ENGINE — NO DATABASE, ONLY LOGIC
# =========================================================
class AttendanceEngine:
    """
    Pure calculation logic.
    No DB calls inside — easy to unit test.
    """

    def __init__(self, policy: AttendancePolicy):
        self.policy = policy

    # -------------------------
    # WORK + BREAK CALCULATION
    # -------------------------
    def compute_work_and_breaks(self, events: List[Dict]):
        total_work = 0
        total_break = 0
        last_start = None
        break_start = None

        day_check_in = None
        last_checkout = None

        for ev in events:
            t = ev["event_time"]
            etype = ev["event_type"]

            if etype == "check_in":
                last_start = t
                day_check_in = t

            elif etype == "break_start" and last_start:
                total_work += (t - last_start).total_seconds()
                break_start = t
                last_start = None

            elif etype == "break_end" and break_start:
                total_break += (t - break_start).total_seconds()
                last_start = t
                break_start = None

            elif etype == "check_out":
                last_checkout = t
                if last_start:
                    total_work += (t - last_start).total_seconds()
                    last_start = None

        day_check_out = last_checkout or day_check_in

        return total_work, total_break, day_check_in, day_check_out

    # -------------------------
    # LATE / EARLY
    # -------------------------
    def compute_late(self, shift, dt, actual_in):
        if not shift or not actual_in:
            return 0, False

        shift_start = datetime.combine(dt, shift["start_time"])
        diff = int((actual_in - shift_start).total_seconds() / 60)

        return (diff, True) if diff > self.policy.late_grace_minutes else (0, False)

    def compute_early(self, shift, dt, actual_out):
        if not shift or not actual_out:
            return 0, False

        end = shift["end_time"]
        is_night = shift.get("is_night_shift", False)

        shift_end = (
            datetime.combine(dt + timedelta(days=1), end)
            if is_night or end <= shift["start_time"]
            else datetime.combine(dt, end)
        )

        diff = int((shift_end - actual_out).total_seconds() / 60)

        return (diff, True) if diff > self.policy.early_exit_grace_minutes else (0, False)

    # -------------------------
    # OVERTIME — NO LATE RECOVERY
    # -------------------------
    def compute_overtime(self, actual_out, shift_end, late_minutes):
        if not self.policy.overtime_enabled:
            return 0, False

        if not actual_out or not shift_end:
            return 0, False

        if actual_out <= shift_end:
            return 0, False

        raw_overtime = int((actual_out - shift_end).total_seconds() / 60)

        adjusted = raw_overtime - late_minutes

        if adjusted <= 0:
            return 0, False

        return adjusted, True

    # -------------------------
    # STATUS DECISION
    # -------------------------
    def decide_status(self, net_hours, required_hours):
        if net_hours >= required_hours * self.policy.full_day_fraction:
            return "present"
        if net_hours >= required_hours * self.policy.half_day_fraction:
            return "half_day"
        return "short_hours"


# =========================================================
# ATTENDANCE SERVICE — orchestrates DB + engine
# =========================================================
class AttendanceService:
    """
    High-level service that:
      ✓ validates actions
      ✓ fetches DB data
      ✓ delegates calculations to engine
      ✓ saves final summary
    """

    # -------------------------
    # PUBLIC EMPLOYEE ACTIONS
    # -------------------------
    @classmethod
    def check_in(cls, employee_id: int, source="manual", meta=None):
        cls._ensure_no_open_checkin(employee_id)

        event = AttendanceEventDB.add_event(employee_id, "check_in", source=source, meta=meta)
        cls.recalculate_for_date(employee_id, event["event_time"].date())
        return event

    @classmethod
    def check_out(cls, employee_id: int, source="manual", meta=None):
        cls._ensure_has_open_checkin(employee_id)

        event = AttendanceEventDB.add_event(employee_id, "check_out", source=source, meta=meta)
        cls.recalculate_for_date(employee_id, event["event_time"].date())
        return event

    @classmethod
    def break_start(cls, employee_id: int, source="manual", meta=None):
        cls._ensure_has_open_checkin(employee_id)
        cls._ensure_no_open_break(employee_id)

        event = AttendanceEventDB.add_event(employee_id, "break_start", source=source, meta=meta)
        cls.recalculate_for_date(employee_id, event["event_time"].date())
        return event

    @classmethod
    def break_end(cls, employee_id: int, source="manual", meta=None):
        cls._ensure_has_open_break(employee_id)

        event = AttendanceEventDB.add_event(employee_id, "break_end", source=source, meta=meta)
        cls.recalculate_for_date(employee_id, event["event_time"].date())
        return event

    # -------------------------
    # CORE RECALCULATION
    # -------------------------
    @classmethod
    def recalculate_for_date(cls, employee_id: int, dt: date):

        # Load policy (thread-safe, per calculation)
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

        events = AttendanceEventDB.get_events_for_window(employee_id, window_start, window_end)

        if not events:
            return cls._handle_no_events(
                employee_id, dt, shift_id, is_weekend, is_holiday, has_leave, is_night_shift
            )

        work_sec, break_sec, check_in, check_out = engine.compute_work_and_breaks(events)

        total_span = (check_out - check_in).total_seconds() if check_in and check_out else 0
        total_hours = round(total_span / 3600, 2)
        net_hours = round(work_sec / 3600, 2)
        break_minutes = int(break_sec / 60)

        late_minutes, is_late = engine.compute_late(shift, dt, check_in)
        early_minutes, is_early = engine.compute_early(shift, dt, check_out)

        # build real shift end datetime
        if shift:
            end = shift["end_time"]
            is_night = shift.get("is_night_shift", False)
            shift_end = datetime.combine(dt + timedelta(days=1), end) if is_night or end <= shift["start_time"] else datetime.combine(dt, end)
        else:
            shift_end = None

        overtime_minutes, is_overtime = engine.compute_overtime(check_out, shift_end, late_minutes)

        status = engine.decide_status(net_hours, required_hours)

        data = {
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
            "is_early_checkout": is_early,
            "is_overtime": is_overtime,
            "is_weekend": is_weekend,
            "is_holiday": is_holiday,
            "is_night_shift": is_night_shift,
            "status": status,
            "is_payroll_locked": False,
            "locked_at": None,
        }

        return AttendanceDB.upsert_full_attendance(data)

    # -------------------------
    # NO-EVENT HANDLER
    # -------------------------
    @classmethod
    def _handle_no_events(cls, employee_id, dt, shift_id, is_weekend, is_holiday, has_leave, is_night):
        if is_holiday:
            status = "holiday"
        elif has_leave:
            status = "on_leave"
        elif is_weekend:
            status = "week_off"
        else:
            status = "absent"

        data = {
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
            "is_night_shift": is_night,
            "status": status,
            "is_payroll_locked": False,
            "locked_at": None,
        }

        return AttendanceDB.upsert_full_attendance(data)

    # -------------------------
    # SHIFT WINDOW BUILDER
    # -------------------------
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

    # -------------------------
    # VALIDATION HELPERS
    # -------------------------
    @classmethod
    def _get_recent_events(cls, employee_id: int):
        now = datetime.now()
        return AttendanceEventDB.get_events_for_window(employee_id, now - timedelta(days=2), now)

    @classmethod
    def _ensure_no_open_checkin(cls, employee_id):
        open_checkin = False
        for ev in cls._get_recent_events(employee_id):
            if ev["event_type"] == "check_in":
                open_checkin = True
            elif ev["event_type"] == "check_out":
                open_checkin = False

        if open_checkin:
            raise AlreadyCheckedIn("Employee is already checked in.")

    @classmethod
    def _ensure_has_open_checkin(cls, employee_id):
        open_checkin = False
        for ev in cls._get_recent_events(employee_id):
            if ev["event_type"] == "check_in":
                open_checkin = True
            elif ev["event_type"] == "check_out":
                open_checkin = False

        if not open_checkin:
            raise NoActiveCheckIn("No active check-in session.")

    @classmethod
    def _ensure_no_open_break(cls, employee_id):
        open_break = False
        for ev in cls._get_recent_events(employee_id):
            if ev["event_type"] == "break_start":
                open_break = True
            elif ev["event_type"] == "break_end":
                open_break = False

        if open_break:
            raise BreakAlreadyRunning("Break already started.")

    @classmethod
    def _ensure_has_open_break(cls, employee_id):
        open_break = False
        for ev in cls._get_recent_events(employee_id):
            if ev["event_type"] == "break_start":
                open_break = True
            elif ev["event_type"] == "break_end":
                open_break = False

        if not open_break:
            raise NoActiveBreak("No active break session to end.")
