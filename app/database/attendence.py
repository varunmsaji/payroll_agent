from datetime import date, datetime
import json
from typing import Optional

from psycopg2.extras import RealDictCursor

from app.database.connection import get_connection


# ==========================================
# ATTENDANCE EVENT FUNCTIONS (RAW LOGS)
# ==========================================
class AttendanceEventDB:

    @staticmethod
    def add_event(
        employee_id: int,
        event_type: str,
        source: str = "manual",
        meta: Optional[dict] = None,
        event_time: Optional[datetime] = None,
    ):
        event_time = event_time or datetime.utcnow()
        meta_json = json.dumps(meta) if meta else None

        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO attendance_events
                        (employee_id, event_type, event_time, source, meta)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *;
                    """,
                    (employee_id, event_type, event_time, source, meta_json),
                )
                return cur.fetchone()

    @staticmethod
    def get_events_for_window(
        employee_id: int,
        start_dt: datetime,
        end_dt: datetime,
    ):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM attendance_events
                    WHERE employee_id = %s
                      AND event_time BETWEEN %s AND %s
                    ORDER BY event_time ASC;
                    """,
                    (employee_id, start_dt, end_dt),
                )
                return cur.fetchall()

    @staticmethod
    def get_all_events_for_employee(employee_id: int):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM attendance_events
                    WHERE employee_id = %s
                    ORDER BY event_time DESC
                    LIMIT 50;
                    """,
                    (employee_id,),
                )
                return cur.fetchall()


# ==========================================
# FULL PAYROLL-GRADE ATTENDANCE DB
# ==========================================
class AttendanceDB:

    @staticmethod
    def get_by_employee_and_date(employee_id: int, dt: date):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM attendance
                    WHERE employee_id = %s
                      AND date = %s
                    LIMIT 1;
                    """,
                    (employee_id, dt),
                )
                return cur.fetchone()

    @staticmethod
    def upsert_full_attendance(data: dict):
        """
        Stores ALL payroll-required columns.
        Respects payroll lock.
        """

        # ✅ Normalize missing keys (CRITICAL)
        REQUIRED_KEYS = [
            "employee_id",
            "shift_id",
            "date",
            "check_in",
            "check_out",
            "total_hours",
            "net_hours",
            "break_minutes",
            "overtime_minutes",
            "late_minutes",
            "early_exit_minutes",
            "is_late",
            "is_early_checkout",
            "is_overtime",
            "is_weekend",
            "is_holiday",
            "is_night_shift",
            "status",
            "is_payroll_locked",
            "locked_at",
        ]

        for key in REQUIRED_KEYS:
            data.setdefault(key, None)

        # Sensible defaults (optional but recommended)
        data.setdefault("break_minutes", 0)
        data.setdefault("overtime_minutes", 0)
        data.setdefault("late_minutes", 0)
        data.setdefault("early_exit_minutes", 0)
        data.setdefault("is_late", False)
        data.setdefault("is_early_checkout", False)
        data.setdefault("is_overtime", False)
        data.setdefault("is_weekend", False)
        data.setdefault("is_holiday", False)
        data.setdefault("is_night_shift", False)
        data.setdefault("is_payroll_locked", False)

        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO attendance (
                        employee_id,
                        shift_id,
                        date,
                        check_in,
                        check_out,
                        total_hours,
                        net_hours,
                        break_minutes,
                        overtime_minutes,
                        late_minutes,
                        early_exit_minutes,
                        is_late,
                        is_early_checkout,
                        is_overtime,
                        is_weekend,
                        is_holiday,
                        is_night_shift,
                        status,
                        is_payroll_locked,
                        locked_at
                    )
                    VALUES (
                        %(employee_id)s,
                        %(shift_id)s,
                        %(date)s,
                        %(check_in)s,
                        %(check_out)s,
                        %(total_hours)s,
                        %(net_hours)s,
                        %(break_minutes)s,
                        %(overtime_minutes)s,
                        %(late_minutes)s,
                        %(early_exit_minutes)s,
                        %(is_late)s,
                        %(is_early_checkout)s,
                        %(is_overtime)s,
                        %(is_weekend)s,
                        %(is_holiday)s,
                        %(is_night_shift)s,
                        %(status)s,
                        %(is_payroll_locked)s,
                        %(locked_at)s
                    )
                    ON CONFLICT (employee_id, date)
                    DO UPDATE SET
                        shift_id           = EXCLUDED.shift_id,
                        check_in           = EXCLUDED.check_in,
                        check_out          = EXCLUDED.check_out,
                        total_hours        = EXCLUDED.total_hours,
                        net_hours          = EXCLUDED.net_hours,
                        break_minutes      = EXCLUDED.break_minutes,
                        overtime_minutes   = EXCLUDED.overtime_minutes,
                        late_minutes       = EXCLUDED.late_minutes,
                        early_exit_minutes = EXCLUDED.early_exit_minutes,
                        is_late            = EXCLUDED.is_late,
                        is_early_checkout  = EXCLUDED.is_early_checkout,
                        is_overtime        = EXCLUDED.is_overtime,
                        is_weekend         = EXCLUDED.is_weekend,
                        is_holiday         = EXCLUDED.is_holiday,
                        is_night_shift     = EXCLUDED.is_night_shift,
                        status             = EXCLUDED.status
                    WHERE attendance.is_payroll_locked = FALSE
                    RETURNING *;
                    """,
                    data,
                )
                return cur.fetchone()


    @staticmethod
    def get_attendance_range(employee_id: int, start_date: date, end_date: date):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM attendance
                    WHERE employee_id = %s
                      AND date BETWEEN %s AND %s
                    ORDER BY date;
                    """,
                    (employee_id, start_date, end_date),
                )
                return cur.fetchall()

    @staticmethod
    def get_attendance(employee_id: int):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM attendance
                    WHERE employee_id = %s
                    ORDER BY date DESC;
                    """,
                    (employee_id,),
                )
                return cur.fetchall()


# ==========================================
# HOLIDAY FUNCTIONS
# ==========================================
class HolidayDB:

    @staticmethod
    def add_holiday(dt: date, name: str, is_optional: bool = False):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO holidays (holiday_date, name, is_optional)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (holiday_date) DO NOTHING
                    RETURNING *;
                    """,
                    (dt, name, is_optional),
                )
                return cur.fetchone()

    @staticmethod
    def is_holiday(dt: date) -> bool:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM holidays WHERE holiday_date = %s;",
                    (dt,),
                )
                return bool(cur.fetchone())


# ==========================================
# SHIFT LOOKUP
# ==========================================
class ShiftDB:

    @staticmethod
    def get_employee_shift(employee_id: int, dt: date):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT s.*
                    FROM employee_shifts es
                    JOIN shifts s ON s.shift_id = es.shift_id
                    WHERE es.employee_id = %s
                      AND es.effective_from <= %s
                      AND (es.effective_to IS NULL OR es.effective_to >= %s)
                    ORDER BY es.effective_from DESC
                    LIMIT 1;
                    """,
                    (employee_id, dt, dt),
                )
                return cur.fetchone()
