# app/database/salary_db.py

from datetime import date
from typing import Optional
from psycopg2.extras import RealDictCursor

from app.database.connection import get_connection


class SalaryDB:

    # ============================================================
    # ✅ EXISTING METHODS (UNCHANGED LOGIC)
    # ============================================================

    @staticmethod
    def add_structure(employee_id, data):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO salary_structure
                    (employee_id, basic, hra, allowances, deductions, effective_from)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    RETURNING *;
                    """,
                    (
                        employee_id,
                        data["basic"],
                        data["hra"],
                        data.get("allowances", 0),
                        data.get("deductions", 0),
                        data["effective_from"],
                    ),
                )
                return cur.fetchone()

    @staticmethod
    def get_structure(employee_id):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM salary_structure
                    WHERE employee_id = %s
                    ORDER BY effective_from DESC;
                    """,
                    (employee_id,),
                )
                return cur.fetchall()

    @staticmethod
    def get_salary_structure(employee_id):
        """Compatibility wrapper"""
        return SalaryDB.get_structure(employee_id)

    # ============================================================
    # ✅ REQUIRED BY PAYROLL SERVICE
    # ============================================================

    @staticmethod
    def get_active_for_date(employee_id: int, for_date: date) -> Optional[dict]:
        """
        Returns the active salary structure for a given date.
        """
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM salary_structure
                    WHERE employee_id = %s
                      AND effective_from <= %s
                      AND (effective_to IS NULL OR effective_to >= %s)
                    ORDER BY effective_from DESC
                    LIMIT 1;
                    """,
                    (employee_id, for_date, for_date),
                )
                return cur.fetchone()

    @staticmethod
    def get_base_salary_from_employee(employee_id: int) -> Optional[float]:
        """
        Payroll fallback if salary structure is missing.
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT base_salary
                    FROM employees
                    WHERE employee_id = %s;
                    """,
                    (employee_id,),
                )
                row = cur.fetchone()

        if not row or row[0] is None:
            return None

        return float(row[0])
