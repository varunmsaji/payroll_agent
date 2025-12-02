from __future__ import annotations

from datetime import datetime, date, time, timedelta
from typing import Optional, Dict, Any

from app.database.attendence import (
    AttendanceDB,
    AttendanceEventDB,
    HolidayDB,
    ShiftDB,
)
from app.database.connection import get_connection


# =====================================
# ATTENDANCE POLICY (DYNAMIC + HISTORY)
# =====================================
class AttendancePolicyDB:
    """
    Reads attendance policy from attendance_policies table.

    ✅ Supports history using created_at:
       - For a given attendance date (dt),
         we pick the latest policy where created_at <= end of that day.
    ✅ If table is missing or empty, we fall back to safe defaults.
    """

    DEFAULT_POLICY = {
        "late_grace_minutes": 10,
        "early_exit_grace_minutes": 10,
        "full_day_fraction": 0.75,
        "half_day_fraction": 0.5,
        "night_shift_enabled": True,
        "overtime_enabled": True,
    }

    @staticmethod
    def get_policy_for_date(dt: date) -> Dict[str, Any]:
        """
        Returns the policy that was active for the given calendar date.

        Logic:
        - Use attendance_policies.created_at as the "effective from" timestamp.
        - For a given dt, pick the LAST row where created_at <= dt 23:59:59.
        - If nothing matches, fall back to DEFAULT_POLICY.
        """
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()

            # We look for the latest policy created on or before the end of that date.
            end_of_day = datetime.combine(dt, time(23, 59, 59))

            cur.execute(
                """
                SELECT
                    late_grace_minutes,
                    early_exit_grace_minutes,
                    full_day_fraction,
                    half_day_fraction,
                    night_shift_enabled,
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
                # No policy yet for that date → default policy
                return AttendancePolicyDB.DEFAULT_POLICY

            # row is a tuple, map accordingly
            return {
                "late_grace_minutes": int(row[0]),
                "early_exit_grace_minutes": int(row[1]),
                "full_day_fraction": float(row[2]),
                "half_day_fraction": float(row[3]),
                "night_shift_enabled": bool(row[4]),
                "overtime_enabled": bool(row[5]),
            }

        except Exception:
            # If table doesn't exist or any DB error → fallback to defaults
            return AttendancePolicyDB.DEFAULT_POLICY

        finally:
            if conn:
                conn.close()


# =====================================
# LEAVE CHECK HELPER
# =====================================
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


# =====================================
# ATTENDANCE SERVICE (FINAL PAYROLL SYNC)
# =====================================
class AttendanceService:
    """
    🔥 NOW DYNAMIC:
    Attendance behaviour is controlled by DB policy (attendance_policies),
    with history support via created_at.

    These attributes are the "currently loaded" policy for the date
    being calculated. They are updated inside recalculate_for_date().
    """

    # Default fallbacks (used if DB table is missing/empty)
    LATE_GRACE_MINUTES = 10
    EARLY_GRACE_MINUTES = 10
    FULL_DAY_FRACTION = 0.75
    HALF_DAY_FRACTION = 0.5

    # --------------------------------------------------
    # EMPLOYEE ACTIONS
    # --------------------------------------------------
    @classmethod
    def check_in(cls, employee_id: int, source: str = "manual", meta: Dict[str, Any] | None = None):
        cls._ensure_no_open_checkin(employee_id)

        event = AttendanceEventDB.add_event(employee_id, "check_in", source=source, meta=meta)
        cls.recalculate_for_date(employee_id, event["event_time"].date())
        return event

    @classmethod
    def check_out(cls, employee_id: int, source: str = "manual", meta: Dict[str, Any] | None = None):
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

    # --------------------------------------------------
    # CORE CALCULATION
    # --------------------------------------------------
    @classmethod
    def recalculate_for_date(cls, employee_id: int, dt: date):

        # 0️⃣ LOAD POLICY FOR THAT DATE (DYNAMIC + HISTORY)
        policy = AttendancePolicyDB.get_policy_for_date(dt)

        cls.LATE_GRACE_MINUTES = int(policy["late_grace_minutes"])
        cls.EARLY_GRACE_MINUTES = int(policy["early_exit_grace_minutes"])
        cls.FULL_DAY_FRACTION = float(policy["full_day_fraction"])
        cls.HALF_DAY_FRACTION = float(policy["half_day_fraction"])

        existing = AttendanceDB.get_by_employee_and_date(employee_id, dt)
        if existing and existing.get("is_payroll_locked"):
            raise ValueError("Attendance locked for payroll.")

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

        work_sec, break_sec, check_in, check_out = cls._compute_work_and_breaks(events)

        total_span_sec = (check_out - check_in).total_seconds() if check_in and check_out else 0
        total_hours = round(total_span_sec / 3600, 2)
        net_hours = round(work_sec / 3600, 2)
        break_minutes = int(break_sec / 60)

        late_minutes, is_late = cls._compute_late(shift, dt, check_in)
        early_exit_minutes, is_early = cls._compute_early_checkout(shift, dt, check_out)
        overtime_minutes, is_overtime = cls._compute_overtime(net_hours, required_hours, policy)

        status = cls._decide_status(net_hours, required_hours, is_weekend, is_holiday, has_leave)

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
            "early_exit_minutes": early_exit_minutes,
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

    # --------------------------------------------------
    # HELPERS
    # --------------------------------------------------
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

    @classmethod
    def _compute_work_and_breaks(cls, events):

        total_work = 0
        total_break = 0
        last_start = None
        break_start = None

        day_check_in = None
        last_checkout = None

        for ev in events:
            t = ev["event_time"]
            etype = ev["event_type"]

            # ✅ CHECK IN
            if etype == "check_in":
                last_start = t
                day_check_in = t

            # ✅ BREAK START (only if working session exists)
            elif etype == "break_start":
                if last_start:
                    total_work += (t - last_start).total_seconds()
                    break_start = t
                    last_start = None

            # ✅ BREAK END (only if valid break was started)
            elif etype == "break_end":
                if break_start:
                    total_break += (t - break_start).total_seconds()
                    last_start = t
                    break_start = None

            # ✅ CHECK OUT (only if working session exists)
            elif etype == "check_out":
                last_checkout = t
                if last_start:
                    total_work += (t - last_start).total_seconds()
                    last_start = None

        day_check_out = last_checkout or day_check_in

        return total_work, total_break, day_check_in, day_check_out

    @classmethod
    def _compute_late(cls, shift, dt, actual_in):
        if not shift or not actual_in:
            return 0, False
        shift_start = datetime.combine(dt, shift["start_time"])
        diff = int((actual_in - shift_start).total_seconds() / 60)
        return (diff, True) if diff > cls.LATE_GRACE_MINUTES else (0, False)

    @classmethod
    def _compute_early_checkout(cls, shift, dt, actual_out):
        if not shift or not actual_out:
            return 0, False
        end = shift["end_time"]
        is_night = shift.get("is_night_shift", False)

        if is_night or end <= shift["start_time"]:
            shift_end = datetime.combine(dt + timedelta(days=1), end)
        else:
            shift_end = datetime.combine(dt, end)

        diff = int((shift_end - actual_out).total_seconds() / 60)
        return (diff, True) if diff > cls.EARLY_GRACE_MINUTES else (0, False)

    @classmethod
    def _compute_overtime(cls, net_hours, required_hours, policy: Dict[str, Any]):
        """
        We keep overtime_minutes calculation here, but whether we PAY for it
        is controlled later by PayrollPolicy (already in your payroll_service).
        """
        # night_shift_enabled, overtime_enabled are available in policy
        overtime_enabled = bool(policy.get("overtime_enabled", True))

        if not overtime_enabled:
            return 0, False

        if net_hours > required_hours:
            mins = int((net_hours - required_hours) * 60)
            return mins, True
        return 0, False

    @classmethod
    def _decide_status(cls, net_hours, required_hours, is_weekend, is_holiday, has_leave):
        # NOTE: We keep weekend/holiday/leave logic as-is.
        # FULL_DAY_FRACTION and HALF_DAY_FRACTION now come from DB policy.
        if net_hours >= required_hours * cls.FULL_DAY_FRACTION:
            return "present"
        elif net_hours >= required_hours * cls.HALF_DAY_FRACTION:
            return "half_day"
        else:
            return "short_hours"

    # --------------------------------------------------
    # SESSION VALIDATORS
    # --------------------------------------------------
    @classmethod
    def _get_recent_events(cls, employee_id: int):
        now = datetime.now()
        return AttendanceEventDB.get_events_for_window(employee_id, now - timedelta(days=2), now)

    @classmethod
    def _ensure_no_open_checkin(cls, employee_id):
        open_ci = False
        for ev in cls._get_recent_events(employee_id):
            if ev["event_type"] == "check_in":
                open_ci = True
            elif ev["event_type"] == "check_out":
                open_ci = False
        if open_ci:
            raise ValueError("Already checked in.")

    @classmethod
    def _ensure_has_open_checkin(cls, employee_id):
        open_ci = False
        for ev in cls._get_recent_events(employee_id):
            if ev["event_type"] == "check_in":
                open_ci = True
            elif ev["event_type"] == "check_out":
                open_ci = False
        if not open_ci:
            raise ValueError("No active check-in.")

    @classmethod
    def _ensure_no_open_break(cls, employee_id):
        open_break = False
        for ev in cls._get_recent_events(employee_id):
            if ev["event_type"] == "break_start":
                open_break = True
            elif ev["event_type"] == "break_end":
                open_break = False
        if open_break:
            raise ValueError("Break already in progress.")

    @classmethod
    def _ensure_has_open_break(cls, employee_id):
        open_break = False
        for ev in cls._get_recent_events(employee_id):
            if ev["event_type"] == "break_start":
                open_break = True
            elif ev["event_type"] == "break_end":
                open_break = False
        if not open_break:
            raise ValueError("No active break to end.")
