# app/database/employee_shift_db.py

from psycopg2.extras import RealDictCursor
from .connection import get_connection
from datetime import date
from typing import Dict, Any



class EmployeeShiftDB:

    # ============================================================
    # ✅ ASSIGN SHIFT (AUTO CLOSE PREVIOUS)
    # ============================================================
    @staticmethod
    def assign_shift(employee_id: int, shift_id: int, effective_from: date):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # ✅ 1. Close any existing active shift
        cur.execute("""
            UPDATE employee_shifts
            SET effective_to = %s
            WHERE employee_id = %s
              AND effective_to IS NULL;
        """, (effective_from, employee_id))

        # ✅ 2. Insert new active shift
        cur.execute("""
            INSERT INTO employee_shifts (
                employee_id,
                shift_id,
                effective_from,
                effective_to
            )
            VALUES (%s, %s, %s, NULL)
            RETURNING *;
        """, (employee_id, shift_id, effective_from))

        res = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return res


    # ============================================================
    # ✅ SHIFT HISTORY (UI TIMELINE)
    # ============================================================
    @staticmethod
    def get_shift_history(employee_id: int):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT 
                es.id,
                s.shift_name,
                s.start_time,
                s.end_time,
                s.is_night_shift,
                es.effective_from,
                es.effective_to
            FROM employee_shifts es
            JOIN shifts s ON s.shift_id = es.shift_id
            WHERE es.employee_id = %s
            ORDER BY es.effective_from DESC;
        """, (employee_id,))

        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows


    # ============================================================
    # ✅ CURRENT ACTIVE SHIFT (ONE ROW GUARANTEED)
    # ============================================================
    @staticmethod
    def get_current_shift(employee_id: int):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT 
                s.shift_id,
                s.shift_name,
                s.start_time,
                s.end_time,
                s.is_night_shift,
                es.effective_from
            FROM employee_shifts es
            JOIN shifts s ON es.shift_id = s.shift_id
            WHERE es.employee_id = %s
              AND es.effective_to IS NULL
            ORDER BY es.effective_from DESC
            LIMIT 1;
        """, (employee_id,))

        res = cur.fetchone()
        cur.close()
        conn.close()
        return res
    
    @staticmethod
    def remove_active_shift(employee_id: int):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            UPDATE employee_shifts
            SET effective_to = CURRENT_DATE
            WHERE employee_id = %s
            AND effective_to IS NULL
            RETURNING *;
        """, (employee_id,))

        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return row

