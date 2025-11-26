# app/database/salary_db.py

from psycopg2.extras import RealDictCursor
from .connection import get_connection


class SalaryDB:

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
