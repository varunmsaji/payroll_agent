# app/database/attendance_db.py

from psycopg2.extras import RealDictCursor
from datetime import datetime
from math import floor
from decimal import Decimal

from .connection import get_connection
from .employee_shift_db import EmployeeShiftDB


# Policy config:
# If True: if employee did NOT record any break events, we will assume they took the allowed break and treat
# actual_break_minutes = allowed_break_minutes (i.e., company enforces break deduction even without punch).
# If False: no auto-grant; only recorded break events count.
AUTO_GRANT_BREAK_IF_NO_PUNCH = False


# ============================================================
# RAW ATTENDANCE EVENTS
# ============================================================
class AttendanceEventDB:

    @staticmethod
    def add_event(employee_id, event_type, source="manual", meta=None):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            INSERT INTO attendance_events
            (employee_id, event_type, event_time, source, meta)
            VALUES (%s,%s,NOW(),%s,%s)
            RETURNING *;
        """, (employee_id, event_type, source, meta))

        res = cur.fetchone()
        conn.commit()
        conn.close()
        return res

    @staticmethod
    def get_events_for_day(employee_id, target_date):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT *
            FROM attendance_events
            WHERE employee_id=%s AND DATE(event_time)=%s
            ORDER BY event_time ASC;
        """, (employee_id, target_date))
        res = cur.fetchall()
        conn.close()
        return res

    @staticmethod
    def get_all_events_for_employee(employee_id):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT *
            FROM attendance_events
            WHERE employee_id=%s
            ORDER BY event_time DESC;
        """, (employee_id,))
        res = cur.fetchall()
        conn.close()
        return res


# ============================================================
# PROCESSED ATTENDANCE (late, OT, break, net hours)
# ============================================================
class AttendanceDB:

    @staticmethod
    def process_attendance(employee_id, day):
        events = AttendanceEventDB.get_events_for_day(employee_id, day)
        if not events:
            return {"error": "No attendance events for the given date"}

        check_in = None
        check_out = None
        break_start = None
        actual_break_minutes = 0

        for ev in events:
            if ev["event_type"] == "check_in" and not check_in:
                check_in = ev["event_time"]

            elif ev["event_type"] == "check_out":
                check_out = ev["event_time"]

            elif ev["event_type"] == "break_start":
                break_start = ev["event_time"]

            elif ev["event_type"] == "break_end" and break_start:
                diff = (ev["event_time"] - break_start).total_seconds() / 60
                actual_break_minutes += floor(diff)
                break_start = None

        # fallback: if no explicit check_out, use last event time
        if not check_out:
            check_out = events[-1]["event_time"]

        # ===== SHIFT DETAILS =====
        shift = EmployeeShiftDB.get_current_shift(employee_id)
        shift_id = shift["shift_id"] if shift else None
        allowed_break_minutes = 0
        if shift:
            allowed_break_minutes = shift.get("break_minutes") or 0

        # ===== Handle auto-grant policy =====
        if actual_break_minutes == 0 and AUTO_GRANT_BREAK_IF_NO_PUNCH and allowed_break_minutes:
            # Company enforces a break even if user didn't punch it
            actual_break_minutes = allowed_break_minutes

        # ===== HOURS CALC =====
        total_hours = round((check_out - check_in).total_seconds() / 3600, 2)

        # Late / overtime calculation (same as before)
        late_minutes = overtime_minutes = 0
        shift_start = shift_end = None
        if shift:
            # shift["start_time"] / ["end_time"] are TIME objects
            shift_start = datetime.combine(day, shift["start_time"])
            shift_end = datetime.combine(day, shift["end_time"])

        if shift_start:
            late_minutes = max(0, floor((check_in - shift_start).total_seconds() / 60))
        if shift_end:
            overtime_minutes = max(0, floor((check_out - shift_end).total_seconds() / 60))

        # ===== Hybrid break logic =====
        # We only deduct the excess minutes beyond allowed. That is:
        # excess = max(0, actual_break_minutes - allowed_break_minutes)
        excess_break_minutes = max(0, actual_break_minutes - (allowed_break_minutes or 0))

        # Net hours = total_hours - excess_break - late + overtime
        net_hours = total_hours - (excess_break_minutes / 60.0)
        net_hours -= (late_minutes / 60.0)
        net_hours += (overtime_minutes / 60.0)
        net_hours = round(net_hours, 2)

        # ===== INSERT / UPDATE ATTENDANCE =====
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # We store actual_break_minutes in the attendance.break_minutes column to preserve history of what was recorded.
        cur.execute("""
           INSERT INTO attendance 
           (employee_id, date, check_in, check_out, total_hours,
            late_minutes, overtime_minutes, break_minutes, net_hours, shift_id)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT (employee_id, date) DO UPDATE SET
               check_in = EXCLUDED.check_in,
               check_out = EXCLUDED.check_out,
               total_hours = EXCLUDED.total_hours,
               late_minutes = EXCLUDED.late_minutes,
               overtime_minutes = EXCLUDED.overtime_minutes,
               break_minutes = EXCLUDED.break_minutes,
               net_hours = EXCLUDED.net_hours,
               shift_id = EXCLUDED.shift_id
           RETURNING *;
        """, (
            employee_id, day, check_in, check_out, total_hours,
            late_minutes, overtime_minutes, actual_break_minutes, net_hours, shift_id
        ))

        res = cur.fetchone()
        conn.commit()
        conn.close()

        # Augment returned result with policy transparency fields (won't be persisted unless you add columns)
        if isinstance(res, dict):
            res["_policy"] = {
                "allowed_break_minutes": allowed_break_minutes,
                "actual_break_minutes": actual_break_minutes,
                "excess_break_minutes": excess_break_minutes,
                "auto_grant_break_if_no_punch": AUTO_GRANT_BREAK_IF_NO_PUNCH
            }

        return res

    @staticmethod
    def get_attendance(employee_id):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT *
            FROM attendance
            WHERE employee_id=%s
            ORDER BY date DESC;
        """, (employee_id,))
        rows = cur.fetchall()
        conn.close()

        converted = []
        for r in rows:
            row = dict(r)

            for key in ("total_hours", "net_hours"):
                if key in row and isinstance(row[key], Decimal):
                    row[key] = float(row[key])

            for key in ("late_minutes", "overtime_minutes", "break_minutes"):
                try:
                    row[key] = int(row[key])
                except:
                    pass

            # Optionally compute and surface policy fields here too (if you want)
            converted.append(row)

        return converted
