import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date, datetime
import json

# ==========================================
# DATABASE CONNECTION
# ==========================================
DB_PARAMS = {
    "dbname": "hrms_db",
    "user": "varun",
    "password": "varun@123",
    "host": "localhost",
    "port": 5432,
}

def get_connection():
    return psycopg2.connect(**DB_PARAMS)


# ==========================================
# ATTENDANCE EVENT FUNCTIONS (RAW LOGS)
# ==========================================
class AttendanceEventDB:

    
    
    @staticmethod
    def add_event(employee_id: int, event_type: str, source="manual", meta=None):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        meta_json = json.dumps(meta) if meta is not None else None

        cur.execute("""
            INSERT INTO attendance_events (employee_id, event_type, event_time, source, meta)
            VALUES (%s, %s, NOW(), %s, %s)
            RETURNING *;
        """, (employee_id, event_type, source, meta_json))

        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return row

    @staticmethod
    def get_events_for_window(employee_id: int, start_dt: datetime, end_dt: datetime):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT *
            FROM attendance_events
            WHERE employee_id = %s
              AND event_time BETWEEN %s AND %s
            ORDER BY event_time ASC;
        """, (employee_id, start_dt, end_dt))

        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows


# ==========================================
# FULL PAYROLL-GRADE ATTENDANCE DB
# ==========================================
class AttendanceDB:

    @staticmethod
    def get_by_employee_and_date(employee_id: int, dt: date):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT *
            FROM attendance
            WHERE employee_id = %s AND date = %s;
        """, (employee_id, dt))

        row = cur.fetchone()
        cur.close()
        conn.close()
        return row


    @staticmethod
    def upsert_full_attendance(data: dict):
        """
        This method stores ALL payroll-required columns.
        It also RESPECTS the payroll lock.
        """
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
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
        """, data)

        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return row
    
    @staticmethod
    def get_attendance_range(employee_id, start_date, end_date):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT *
            FROM attendance
            WHERE employee_id = %s
              AND date BETWEEN %s AND %s
            ORDER BY date;
        """, (employee_id, start_date, end_date))

        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows



# ==========================================
# HOLIDAY FUNCTIONS
# ==========================================
class HolidayDB:

    @staticmethod
    def add_holiday(dt: date, name: str, is_optional=False):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            INSERT INTO holidays (holiday_date, name, is_optional)
            VALUES (%s, %s, %s)
            ON CONFLICT (holiday_date) DO NOTHING
            RETURNING *;
        """, (dt, name, is_optional))

        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return row

    @staticmethod
    def is_holiday(dt: date):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM holidays WHERE holiday_date = %s;", (dt,))
        result = cur.fetchone()

        cur.close()
        conn.close()
        return bool(result)


# ==========================================
# SHIFT LOOKUP
# ==========================================
class ShiftDB:

    @staticmethod
    def get_employee_shift(employee_id: int, dt: date):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT s.*
            FROM employee_shifts es
            JOIN shifts s ON s.shift_id = es.shift_id
            WHERE es.employee_id = %s
              AND es.effective_from <= %s
              AND (es.effective_to IS NULL OR es.effective_to >= %s)
            ORDER BY es.effective_from DESC
            LIMIT 1;
        """, (employee_id, dt, dt))

        row = cur.fetchone()
        cur.close()
        conn.close()
        return row