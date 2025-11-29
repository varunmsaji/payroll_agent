# app/database/payroll_db.py

from datetime import date
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from .connection import get_connection


class SalaryStructureDB:
    """
    Minimal helper to get salary structure for an employee.
    Uses salary_structure table, falls back to employees.base_salary if needed.
    """

    @staticmethod
    def get_active_for_date(employee_id: int, for_date: date) -> Optional[dict]:
        """
        Get the latest salary structure row active on a given date.
        """
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

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
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row

    @staticmethod
    def get_base_salary_from_employee(employee_id: int) -> Optional[float]:
        """
        Fallback: if salary_structure is not defined, use employees.base_salary.
        """
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT base_salary
            FROM employees
            WHERE employee_id = %s;
            """,
            (employee_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row is None:
            return None
        return float(row[0]) if row[0] is not None else None


class PayrollDB:
    """
    DB helper for payroll table and attendance locking.
    """

    @staticmethod
    def upsert_payroll(
        employee_id: int,
        year: int,
        month: int,
        working_days: int,
        present_days: int,
        total_hours: float,
        gross_salary: float,
        net_salary: float,
    ) -> dict:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            INSERT INTO payroll (
                employee_id,
                month,
                year,
                working_days,
                present_days,
                total_hours,
                gross_salary,
                net_salary
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (employee_id, month, year)
            DO UPDATE SET
                working_days = EXCLUDED.working_days,
                present_days = EXCLUDED.present_days,
                total_hours  = EXCLUDED.total_hours,
                gross_salary = EXCLUDED.gross_salary,
                net_salary   = EXCLUDED.net_salary,
                generated_at = NOW()
            RETURNING *;
            """,
            (
                employee_id,
                month,
                year,
                working_days,
                present_days,
                total_hours,
                gross_salary,
                net_salary,
            ),
        )

        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return row

    @staticmethod
    def get_payroll(employee_id: int, year: int, month: int) -> Optional[dict]:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT *
            FROM payroll
            WHERE employee_id = %s AND year = %s AND month = %s;
            """,
            (employee_id, year, month),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row

    @staticmethod
    def lock_attendance_for_period(employee_id: int, start_date: date, end_date: date) -> None:
        """
        Lock all attendance rows for that employee in the month, after payroll generation.
        """
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE attendance
            SET is_payroll_locked = TRUE,
                locked_at = NOW()
            WHERE employee_id = %s
              AND date BETWEEN %s AND %s;
            """,
            (employee_id, start_date, end_date),
        )

        conn.commit()
        cur.close()
        conn.close()
