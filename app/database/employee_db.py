# app/database/employee_db.py

from psycopg2.extras import RealDictCursor
from app.database.connection import get_connection


class EmployeeDB:

    # ============================
    # ✅ ADD EMPLOYEE (WITH MANAGER)
    # ============================
    @staticmethod
    def add_employee(data):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            INSERT INTO employees
            (first_name, last_name, email, phone, designation, department, 
             date_of_joining, base_salary, manager_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING *;
        """, (
            data["first_name"], data["last_name"], data["email"], data["phone"],
            data["designation"], data["department"], data["date_of_joining"],
            data["base_salary"], data.get("manager_id")
        ))

        res = cur.fetchone()
        conn.commit()
        conn.close()
        return res

    # ============================
    # ✅ GET ALL EMPLOYEES
    # ============================
    @staticmethod
    def get_all():
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT e.*, 
                   m.first_name AS manager_first_name,
                   m.last_name AS manager_last_name
            FROM employees e
            LEFT JOIN employees m ON e.manager_id = m.employee_id
            ORDER BY e.employee_id DESC;
        """)

        res = cur.fetchall()
        conn.close()
        return res

    # ============================
    # ✅ GET ONE EMPLOYEE
    # ============================
    @staticmethod
    def get_one(employee_id):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT e.*, 
                   m.first_name AS manager_first_name,
                   m.last_name AS manager_last_name
            FROM employees e
            LEFT JOIN employees m ON e.manager_id = m.employee_id
            WHERE e.employee_id=%s;
        """, (employee_id,))

        res = cur.fetchone()
        conn.close()
        return res

    # ============================
    # ✅ UPDATE EMPLOYEE (WITH MANAGER)
    # ============================
    @staticmethod
    def update_employee(employee_id, data):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            UPDATE employees
            SET first_name=%s, last_name=%s, email=%s, phone=%s,
                designation=%s, department=%s, base_salary=%s,
                manager_id=%s
            WHERE employee_id=%s
            RETURNING *;
        """, (
            data["first_name"], data["last_name"], data["email"], data["phone"],
            data["designation"], data["department"], data["base_salary"],
            data.get("manager_id"),
            employee_id
        ))

        res = cur.fetchone()
        conn.commit()
        conn.close()
        return res

    # ============================
    # ✅ SET / CHANGE MANAGER ONLY
    # ============================
    @staticmethod
    def set_manager(employee_id, manager_id):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            UPDATE employees
            SET manager_id=%s
            WHERE employee_id=%s
            RETURNING *;
        """, (manager_id, employee_id))

        res = cur.fetchone()
        conn.commit()
        conn.close()
        return res

    # ============================
    # ✅ GET MANAGER FOR WORKFLOW AUTO-ASSIGN
    # ============================
    @staticmethod
    def get_manager_id(employee_id):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT manager_id FROM employees
            WHERE employee_id=%s;
        """, (employee_id,))

        row = cur.fetchone()
        conn.close()
        return row[0] if row else None

    # ============================
    # ✅ GET ALL MANAGERS (FOR DROPDOWNS)
    # ============================
    @staticmethod
    def get_all_managers():
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT employee_id, first_name, last_name
            FROM employees
            WHERE designation ILIKE '%manager%' 
               OR designation ILIKE '%lead%' 
               OR designation ILIKE '%head%';
        """)

        res = cur.fetchall()
        conn.close()
        return res

    # ============================
    # ✅ DELETE EMPLOYEE
    # ============================
    @staticmethod
    def delete_employee(employee_id):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("DELETE FROM employees WHERE employee_id=%s;", (employee_id,))
        conn.commit()
        conn.close()
        return True
        # ============================
    # ✅ GET HR USER
    # ============================
    @staticmethod
    def get_hr_user():
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT employee_id 
            FROM employees
            WHERE department ILIKE '%hr%' 
            ORDER BY employee_id LIMIT 1
        """)

        row = cur.fetchone()
        conn.close()
        return row[0] if row else None

    # ============================
    # ✅ GET FINANCE HEAD
    # ============================
    @staticmethod
    def get_finance_head():
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT employee_id 
            FROM employees
            WHERE department ILIKE '%finance%' 
            ORDER BY employee_id LIMIT 1
        """)

        row = cur.fetchone()
        conn.close()
        return row[0] if row else None

    # ============================
    # ✅ GET DIRECTOR / CEO
    # ============================
    @staticmethod
    def get_director():
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT employee_id 
            FROM employees
            WHERE designation ILIKE '%director%' 
               OR designation ILIKE '%ceo%'
            ORDER BY employee_id LIMIT 1
        """)

        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
