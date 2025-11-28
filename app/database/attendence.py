# app/database/attendance_db.py

from psycopg2.extras import RealDictCursor
from datetime import datetime, date
from math import floor
from decimal import Decimal

from .connection import get_connection
from .employee_shift_db import EmployeeShiftDB


# ============================================================
# POLICY FLAGS
# ============================================================

# If True: if employee did NOT record any break events, we assume they took the
# allowed break and deduct it. If False: only recorded break is counted.
AUTO_GRANT_BREAK_IF_NO_PUNCH = False


# ============================================================
# RAW ATTENDANCE EVENTS
# ============================================================
class AttendanceEventDB:

    VALID_EVENT_TYPES = {"check_in", "check_out", "break_start", "break_end"}

    @staticmethod
    def add_event(employee_id, event_type, source="manual", meta=None):
        """
        Hardened:
        - Validates event_type
        - Prevents double check-in
        - Prevents check-out without prior check-in
        - Prevents multiple check-outs
        - Prevents break_start if previous break not ended
        - Prevents break_end if no open break
        Returns:
            - dict(row) on success
            - {"error": "..."} on validation failure
        """
        if event_type not in AttendanceEventDB.VALID_EVENT_TYPES:
            return {"error": f"Invalid event_type: {event_type}"}

        today = datetime.now().date()
        events_today = AttendanceEventDB.get_events_for_day(employee_id, today)

        # Helper flags
        has_check_in = any(e["event_type"] == "check_in" for e in events_today)
        has_check_out = any(e["event_type"] == "check_out" for e in events_today)

        # Determine if there is an "open" break
        open_break = False
        for e in events_today:
            if e["event_type"] == "break_start" and not open_break:
                open_break = True
            elif e["event_type"] == "break_end" and open_break:
                open_break = False

        # ============================
        # VALIDATION RULES
        # ============================

        # 1️⃣ CHECK-IN
        if event_type == "check_in":
            if has_check_in:
                return {"error": "Check-in already recorded for today"}

        # 2️⃣ CHECK-OUT
        elif event_type == "check_out":
            if not has_check_in:
                return {"error": "Cannot check-out without a check-in today"}
            if has_check_out:
                return {"error": "Check-out already recorded for today"}

        # 3️⃣ BREAK START
        elif event_type == "break_start":
            if not has_check_in:
                return {"error": "Cannot start break before check-in"}
            if open_break:
                return {"error": "Previous break not ended; cannot start another break"}

        # 4️⃣ BREAK END
        elif event_type == "break_end":
            if not has_check_in:
                return {"error": "Cannot end break before check-in"}
            if not open_break:
                return {"error": "No active break to end"}

        # ============================
        # IF VALID → INSERT EVENT
        # ============================
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

    # ----------------------------------------
    # MAIN PROCESSOR
    # ----------------------------------------
    @staticmethod
    def process_attendance(employee_id, day: date):
        """
        Processes one day's attendance for an employee.

        Hardened:
        - Does nothing if no events for that day
        - Respects attendance.is_locked (no overwrite)
        - Returns {"error": "..."} if locked
        """
        events = AttendanceEventDB.get_events_for_day(employee_id, day)
        if not events:
            return {"error": "No attendance events for the given date"}

        check_in = None
        check_out = None
        break_start = None
        actual_break_minutes = 0

        # ========= Parse events =========
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

        # Fallback: if no explicit check_out, use last event time
        if not check_out:
            check_out = events[-1]["event_time"]

        # ========= SHIFT DETAILS =========
        shift = EmployeeShiftDB.get_current_shift(employee_id)
        shift_id = shift["shift_id"] if shift else None
        allowed_break_minutes = 0
        if shift:
            allowed_break_minutes = shift.get("break_minutes") or 0

        # ========= Auto-grant break policy =========
        if actual_break_minutes == 0 and AUTO_GRANT_BREAK_IF_NO_PUNCH and allowed_break_minutes:
            actual_break_minutes = allowed_break_minutes

        # ========= HOURS CALC =========
        total_hours = round((check_out - check_in).total_seconds() / 3600, 2)

        late_minutes = overtime_minutes = 0
        shift_start = shift_end = None

        if shift:
            shift_start = datetime.combine(day, shift["start_time"])
            shift_end = datetime.combine(day, shift["end_time"])

        if shift_start:
            late_minutes = max(0, floor((check_in - shift_start).total_seconds() / 60))
        if shift_end:
            overtime_minutes = max(0, floor((check_out - shift_end).total_seconds() / 60))

        # ========= Hybrid break logic =========
        # Only deduct EXCESS over allowed
        excess_break_minutes = max(0, actual_break_minutes - (allowed_break_minutes or 0))

        net_hours = total_hours
        net_hours -= (excess_break_minutes / 60.0)
        net_hours -= (late_minutes / 60.0)
        net_hours += (overtime_minutes / 60.0)
        net_hours = round(net_hours, 2)

        # ========= INSERT / UPDATE ATTENDANCE =========
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
           INSERT INTO attendance 
           (employee_id, date, check_in, check_out, total_hours,
            late_minutes, overtime_minutes, break_minutes, net_hours, shift_id, is_locked)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,FALSE)
           ON CONFLICT (employee_id, date) DO UPDATE SET
               check_in = EXCLUDED.check_in,
               check_out = EXCLUDED.check_out,
               total_hours = EXCLUDED.total_hours,
               late_minutes = EXCLUDED.late_minutes,
               overtime_minutes = EXCLUDED.overtime_minutes,
               break_minutes = EXCLUDED.break_minutes,
               net_hours = EXCLUDED.net_hours,
               shift_id = EXCLUDED.shift_id
           WHERE attendance.is_locked = FALSE
           RETURNING *;
        """, (
            employee_id, day, check_in, check_out, total_hours,
            late_minutes, overtime_minutes, actual_break_minutes, net_hours, shift_id
        ))

        res = cur.fetchone()
        conn.commit()
        conn.close()

        # If locked, RETURNING will be empty → res is None
        if not res:
            return {"error": "Attendance is locked for this date and cannot be modified"}

        # Add policy info to response (not stored in DB)
        res = dict(res)
        res["_policy"] = {
            "allowed_break_minutes": allowed_break_minutes,
            "actual_break_minutes": actual_break_minutes,
            "excess_break_minutes": excess_break_minutes,
            "auto_grant_break_if_no_punch": AUTO_GRANT_BREAK_IF_NO_PUNCH
        }

        return res

    # ----------------------------------------
    # GET ALL ATTENDANCE FOR EMPLOYEE
    # ----------------------------------------
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

            # Convert Decimal → float
            for key in ("total_hours", "net_hours"):
                if key in row and isinstance(row[key], Decimal):
                    row[key] = float(row[key])

            # Convert numeric minutes to int
            for key in ("late_minutes", "overtime_minutes", "break_minutes"):
                try:
                    row[key] = int(row[key])
                except Exception:
                    pass

            converted.append(row)

        return converted

    # ----------------------------------------
    # LOCK / UNLOCK ATTENDANCE (FOR PAYROLL)
    # ----------------------------------------
    @staticmethod
    def lock_month(month: int, year: int, employee_id: int = None):
        """
        Mark attendance rows as locked for given month/year.
        Once locked, process_attendance cannot overwrite them.
        """
        conn = get_connection()
        cur = conn.cursor()

        if employee_id:
            cur.execute("""
                UPDATE attendance
                SET is_locked = TRUE
                WHERE EXTRACT(MONTH FROM date)=%s
                  AND EXTRACT(YEAR FROM date)=%s
                  AND employee_id=%s;
            """, (month, year, employee_id))
        else:
            cur.execute("""
                UPDATE attendance
                SET is_locked = TRUE
                WHERE EXTRACT(MONTH FROM date)=%s
                  AND EXTRACT(YEAR FROM date)=%s;
            """, (month, year))

        conn.commit()
        conn.close()
        return {"locked": True}

    @staticmethod
    def unlock_day(employee_id: int, day: date):
        """
        Admin-only: unlock a specific day's attendance to allow correction.
        """
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE attendance
            SET is_locked = FALSE
            WHERE employee_id=%s AND date=%s;
        """, (employee_id, day))
        conn.commit()
        conn.close()
        return {"unlocked": True}
