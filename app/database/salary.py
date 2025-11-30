# app/database/salary_db.py

from datetime import date
from typing import Optional
from psycopg2.extras import RealDictCursor
from .connection import get_connection


class SalaryDB:

    # ============================================================
    # ✅ YOUR EXISTING METHODS (UNCHANGED)
    # ============================================================

    @staticmethod
    def add_structure(employee_id, data):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            INSERT INTO salary_structure
            (employee_id, basic, hra, allowances, deductions, effective_from)
            VALUES (%s,%s,%s,%s,%s,%s)
            RETURNING *;
        """, (
            employee_id,
            data["basic"],
            data["hra"],
            data.get("allowances", 0),
            data.get("deductions", 0),
            data["effective_from"]
        ))

        res = cur.fetchone()
        conn.commit()
        conn.close()
        return res

    @staticmethod
    def get_structure(employee_id):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT *
            FROM salary_structure
            WHERE employee_id=%s
            ORDER BY effective_from DESC;
        """, (employee_id,))

        res = cur.fetchall()
        conn.close()
        return res

    @staticmethod
    def get_salary_structure(employee_id):
        """Compatibility wrapper"""
        return SalaryDB.get_structure(employee_id)

    # ============================================================
    # ✅ ✅ NEW METHODS REQUIRED BY PAYROLL SERVICE
    # ============================================================

    @staticmethod
    def get_active_for_date(employee_id: int, for_date: date) -> Optional[dict]:
        """
        ✅ This is REQUIRED by PayrollService
        """
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT *
            FROM salary_structure
            WHERE employee_id = %s
              AND effective_from <= %s
              AND (effective_to IS NULL OR effective_to >= %s)
            ORDER BY effective_from DESC
            LIMIT 1;
        """, (employee_id, for_date, for_date))

        row = cur.fetchone()
        cur.close()
        conn.close()
        return row

    @staticmethod
    def get_base_salary_from_employee(employee_id: int) -> Optional[float]:
        """
        ✅ Payroll fallback if structure missing
        """
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT base_salary
            FROM employees
            WHERE employee_id = %s;
        """, (employee_id,))

        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return None
        return float(row[0]) if row[0] is not None else None
