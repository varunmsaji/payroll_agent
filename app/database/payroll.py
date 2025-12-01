# app/database/payroll_db.py

from datetime import date
from psycopg2.extras import RealDictCursor
from app.database.connection import get_connection


# ============================================================
# ✅ PAYROLL DATABASE (FULL PERSISTENCE)
# ============================================================

class PayrollDB:

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

        basic_pay: float,
        hra_pay: float,
        allowances_pay: float,

        overtime_hours: float,
        overtime_pay: float,

        lop_days: float,
        lop_deduction: float,

        late_penalty: float,
        early_penalty: float,

        holiday_pay: float,
        night_shift_allowance: float,

        is_finalized: bool = False,
    ):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            INSERT INTO payroll (
                employee_id,
                month,
                year,

                working_days,
                present_days,
                total_hours,

                gross_salary,
                net_salary,

                basic_pay,
                hra_pay,
                allowances_pay,

                overtime_hours,
                overtime_pay,

                lop_days,
                lop_deduction,

                late_penalty,
                early_penalty,

                holiday_pay,
                night_shift_allowance,

                is_finalized,
                generated_at
            )
            VALUES (
                %s,%s,%s,

                %s,%s,%s,

                %s,%s,

                %s,%s,%s,

                %s,%s,

                %s,%s,

                %s,%s,

                %s,%s,

                %s,
                NOW()
            )
            ON CONFLICT (employee_id, month, year)
            DO UPDATE SET

                working_days = EXCLUDED.working_days,
                present_days = EXCLUDED.present_days,
                total_hours = EXCLUDED.total_hours,

                gross_salary = EXCLUDED.gross_salary,
                net_salary = EXCLUDED.net_salary,

                basic_pay = EXCLUDED.basic_pay,
                hra_pay = EXCLUDED.hra_pay,
                allowances_pay = EXCLUDED.allowances_pay,

                overtime_hours = EXCLUDED.overtime_hours,
                overtime_pay = EXCLUDED.overtime_pay,

                lop_days = EXCLUDED.lop_days,
                lop_deduction = EXCLUDED.lop_deduction,

                late_penalty = EXCLUDED.late_penalty,
                early_penalty = EXCLUDED.early_penalty,

                holiday_pay = EXCLUDED.holiday_pay,
                night_shift_allowance = EXCLUDED.night_shift_allowance,

                is_finalized = EXCLUDED.is_finalized,
                generated_at = NOW()

            RETURNING *;
        """, (
            employee_id,
            month,
            year,

            working_days,
            present_days,
            total_hours,

            gross_salary,
            net_salary,

            basic_pay,
            hra_pay,
            allowances_pay,

            overtime_hours,
            overtime_pay,

            lop_days,
            lop_deduction,

            late_penalty,
            early_penalty,

            holiday_pay,
            night_shift_allowance,

            is_finalized
        ))

        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return row

    @staticmethod
    def get_payroll(employee_id: int, month: int, year: int):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT *
            FROM payroll
            WHERE employee_id = %s
              AND month = %s
              AND year = %s;
        """, (employee_id, month, year))

        row = cur.fetchone()
        cur.close()
        conn.close()
        return row

    @staticmethod
    def lock_attendance_for_period(employee_id: int, start_date: date, end_date: date):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE attendance
            SET
                is_payroll_locked = TRUE,
                locked_at = NOW()
            WHERE employee_id = %s
              AND date BETWEEN %s AND %s;
        """, (employee_id, start_date, end_date))

        conn.commit()
        cur.close()
        conn.close()
        return True


# ============================================================
# ✅ PAYROLL POLICY DATABASE (ADMIN CONTROL)
# ============================================================

class PayrollPolicyDB:

    @staticmethod
    def get_active_policy():
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT *
            FROM payroll_policies
            WHERE active = TRUE
            ORDER BY created_at DESC
            LIMIT 1;
        """)

        policy = cur.fetchone()
        cur.close()
        conn.close()
        return policy

    @staticmethod
    def update_policy(data: dict):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("UPDATE payroll_policies SET active = FALSE;")

        cur.execute("""
            INSERT INTO payroll_policies (
                late_grace_minutes,
                late_lop_threshold_minutes,
                early_exit_grace_minutes,
                early_exit_lop_threshold_minutes,
                overtime_enabled,
                overtime_multiplier,
                holiday_double_pay,
                weekend_paid_only_if_worked,
                night_shift_allowance,
                active
            )
            VALUES (
                %(late_grace_minutes)s,
                %(late_lop_threshold_minutes)s,
                %(early_exit_grace_minutes)s,
                %(early_exit_lop_threshold_minutes)s,
                %(overtime_enabled)s,
                %(overtime_multiplier)s,
                %(holiday_double_pay)s,
                %(weekend_paid_only_if_worked)s,
                %(night_shift_allowance)s,
                TRUE
            )
            RETURNING *;
        """, data)

        policy = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return policy
