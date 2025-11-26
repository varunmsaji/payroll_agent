# app/database/employee_shift_db.py

from psycopg2.extras import RealDictCursor
from .connection import get_connection

class EmployeeShiftDB:

    @staticmethod
    def assign_shift(employee_id, shift_id, effective_from):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO employee_shifts (employee_id, shift_id, effective_from)
            VALUES (%s,%s,%s)
            RETURNING *;
        """, (employee_id, shift_id, effective_from))
        res = cur.fetchone()
        conn.commit()
        conn.close()
        return res

    @staticmethod
    def get_shift_history(employee_id):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT es.*, s.shift_name, s.start_time, s.end_time, s.is_night_shift
            FROM employee_shifts es
            JOIN shifts s ON s.shift_id = es.shift_id
            WHERE es.employee_id=%s
            ORDER BY es.effective_from DESC;
        """, (employee_id,))
        rows = cur.fetchall()
        conn.close()
        return rows

    @staticmethod
    def get_current_shift(employee_id):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT es.*, s.shift_name, s.start_time, s.end_time
            FROM employee_shifts es
            JOIN shifts s ON es.shift_id = s.shift_id
            WHERE employee_id=%s
              AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)
            ORDER BY effective_from DESC LIMIT 1;
        """, (employee_id,))
        res = cur.fetchone()
        conn.close()
        return res
