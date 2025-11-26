# app/database/payroll_db.py

from psycopg2.extras import RealDictCursor
from .connection import get_connection


class PayrollDB:

    @staticmethod
    def generate(employee_id, month, year):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Total net hours
        cur.execute("""
            SELECT SUM(net_hours) AS hrs, COUNT(*) AS present_days
            FROM attendance
            WHERE employee_id=%s
              AND EXTRACT(MONTH FROM date)=%s
              AND EXTRACT(YEAR FROM date)=%s;
        """, (employee_id, month, year))

        result = cur.fetchone()
        net_hours = result["hrs"] or 0
        present_days = result["present_days"]

        # Get salary structure
        cur.execute("""
            SELECT *
            FROM salary_structure
            WHERE employee_id=%s
            ORDER BY effective_from DESC LIMIT 1;
        """, (employee_id,))
        sal = cur.fetchone()

        if not sal:
            gross_salary = net_salary = 0
        else:
            gross_salary = sal["basic"] + sal["hra"] + sal["allowances"]
            net_salary = gross_salary - sal["deductions"]

        # Insert/update payroll
        cur.execute("""
            INSERT INTO payroll
            (employee_id, month, year, working_days, present_days, total_hours,
             gross_salary, net_salary)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (employee_id, month, year) DO UPDATE SET
                present_days=EXCLUDED.present_days,
                total_hours=EXCLUDED.total_hours,
                gross_salary=EXCLUDED.gross_salary,
                net_salary=EXCLUDED.net_salary
            RETURNING *;
        """, (
            employee_id, month, year,
            26, present_days, net_hours,
            gross_salary, net_salary
        ))

        res = cur.fetchone()
        conn.commit()
        conn.close()
        return res

    @staticmethod
    def get_payroll(employee_id, month, year):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT *
            FROM payroll
            WHERE employee_id=%s AND month=%s AND year=%s;
        """, (employee_id, month, year))
        res = cur.fetchone()
        conn.close()
        return res
