# app/database/employee_db.py

from psycopg2.extras import RealDictCursor
from app.database.connection import get_connection


class EmployeeDB:

    # ============================
    # ✅ ADD EMPLOYEE (SAFE)
    # ============================
    @staticmethod
    def add_employee(data):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO employees
                    (first_name, last_name, email, phone, designation, department,
                     date_of_joining, base_salary, manager_id, status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'active')
                    RETURNING *;
                    """,
                    (
                        data["first_name"],
                        data["last_name"],
                        data["email"],
                        data["phone"],
                        data["designation"],
                        data["department"],
                        data["date_of_joining"],
                        data["base_salary"],
                        data.get("manager_id"),
                    ),
                )
                return cur.fetchone()

    # ============================
    # ✅ ACTIVE CHECK
    # ============================
    @staticmethod
    def is_active(employee_id):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status FROM employees WHERE employee_id=%s;",
                    (employee_id,),
                )
                row = cur.fetchone()
                return row and row[0] == "active"

    # ============================
    # ✅ GET ALL (PAGINATED)
    # ============================
    @staticmethod
    def get_all(page=1, limit=50, status=""):
        offset = (page - 1) * limit

        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if status:
                    cur.execute(
                        """
                        SELECT * FROM employees
                        WHERE status=%s
                        ORDER BY employee_id DESC
                        LIMIT %s OFFSET %s
                        """,
                        (status, limit, offset),
                    )
                else:
                    cur.execute(
                        """
                        SELECT * FROM employees
                        ORDER BY employee_id DESC
                        LIMIT %s OFFSET %s
                        """,
                        (limit, offset),
                    )
                return cur.fetchall()

    # ============================
    # ✅ GET ONE
    # ============================
    @staticmethod
    def get_one(employee_id):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM employees WHERE employee_id=%s;",
                    (employee_id,),
                )
                return cur.fetchone()

    # ============================
    # ✅ SAFE MANAGER ASSIGNMENT (NO LOOPS)
    # ============================
    @staticmethod
    def set_manager(employee_id, manager_id):

        if employee_id == manager_id:
            raise Exception("Employee cannot be their own manager")

        # ✅ Prevent circular chain
        parent = manager_id
        while parent:
            if parent == employee_id:
                raise Exception("Circular manager assignment detected")
            parent = EmployeeDB.get_manager_id(parent)

        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE employees
                    SET manager_id=%s
                    WHERE employee_id=%s
                    RETURNING *;
                    """,
                    (manager_id, employee_id),
                )
                return cur.fetchone()

    # ============================
    # ✅ SOFT DELETE (EX-EMPLOYEE)
    # ============================
    @staticmethod
    def deactivate_employee(employee_id):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE employees
                    SET status='ex_employee'
                    WHERE employee_id=%s
                    RETURNING *;
                    """,
                    (employee_id,),
                )
                return cur.fetchone()

    # ============================
    # ✅ MANAGER / HR / FINANCE / DIRECTOR
    # ============================
    @staticmethod
    def get_manager_id(employee_id):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT manager_id FROM employees WHERE employee_id=%s;",
                    (employee_id,),
                )
                row = cur.fetchone()
                return row[0] if row else None

    @staticmethod
    def get_hr_user():
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT employee_id FROM employees WHERE designation='HR' LIMIT 1"
                )
                row = cur.fetchone()
                return row[0] if row else None

    @staticmethod
    def get_finance_head():
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT employee_id FROM employees WHERE designation='finance' LIMIT 1"
                )
                row = cur.fetchone()
                return row[0] if row else None

    @staticmethod
    def get_director():
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT employee_id FROM employees WHERE designation='director' LIMIT 1"
                )
                row = cur.fetchone()
                return row[0] if row else None

    @staticmethod
    def get_all_managers():
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT employee_id, first_name, last_name, designation
                    FROM employees
                    WHERE status='active'
                      AND (
                            designation ILIKE '%manager%' OR
                            designation ILIKE '%lead%' OR
                            designation ILIKE '%head%'
                          )
                    ORDER BY first_name;
                    """
                )
                return cur.fetchall()
