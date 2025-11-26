# app/database/employee_db.py

from psycopg2.extras import RealDictCursor
from app.database.connection import get_connection

class EmployeeDB:

    @staticmethod
    def add_employee(data):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            INSERT INTO employees
            (first_name, last_name, email, phone, designation, department, date_of_joining, base_salary)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING *;
        """, (
            data["first_name"], data["last_name"], data["email"], data["phone"],
            data["designation"], data["department"], data["date_of_joining"],
            data["base_salary"]
        ))

        res = cur.fetchone()
        conn.commit()
        conn.close()
        return res

    @staticmethod
    def get_all():
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM employees ORDER BY employee_id DESC;")
        res = cur.fetchall()
        conn.close()
        return res

    @staticmethod
    def get_one(employee_id):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM employees WHERE employee_id=%s;", (employee_id,))
        res = cur.fetchone()
        conn.close()
        return res

    @staticmethod
    def update_employee(employee_id, data):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            UPDATE employees
            SET first_name=%s, last_name=%s, email=%s, phone=%s,
                designation=%s, department=%s, base_salary=%s
            WHERE employee_id=%s
            RETURNING *;
        """, (
            data["first_name"], data["last_name"], data["email"], data["phone"],
            data["designation"], data["department"], data["base_salary"],
            employee_id
        ))

        res = cur.fetchone()
        conn.commit()
        conn.close()
        return res

    @staticmethod
    def delete_employee(employee_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM employees WHERE employee_id=%s;", (employee_id,))
        conn.commit()
        conn.close()
        return True
