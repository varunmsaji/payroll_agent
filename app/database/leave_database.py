from datetime import date
from psycopg2.extras import RealDictCursor

from app.database.connection import get_connection


# ===============================================
#  HELPER: EMPLOYEE SALARY (for payroll)
# ===============================================
class EmployeeSalaryDB:

    @staticmethod
    def get_base_salary(employee_id: int):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT base_salary
                    FROM employees
                    WHERE employee_id=%s;
                    """,
                    (employee_id,),
                )
                return cur.fetchone()


# ===============================================
#  LEAVE TYPES CRUD
# ===============================================
class LeaveTypeDB:

    @staticmethod
    def add_leave_type(name, code, yearly_quota=0, is_paid=True, carry_forward=True):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO leave_types (name, code, yearly_quota, is_paid, carry_forward)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *;
                    """,
                    (name, code, yearly_quota, is_paid, carry_forward),
                )
                return cur.fetchone()

    @staticmethod
    def get_leave_types():
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM leave_types ORDER BY leave_type_id;"
                )
                return cur.fetchall()

    @staticmethod
    def get_leave_type(leave_type_id: int):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM leave_types WHERE leave_type_id=%s;",
                    (leave_type_id,),
                )
                return cur.fetchone()


# ===============================================
#  LEAVE BALANCE CRUD / VALIDATION
# ===============================================
class LeaveBalanceDB:

    @staticmethod
    def initialize_balance(employee_id, leave_type_id, year, quota, carry_forwarded=0):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO employee_leave_balance
                    (employee_id, leave_type_id, year, total_quota, used, remaining, carry_forwarded)
                    VALUES (%s, %s, %s, %s, 0, %s, %s)
                    ON CONFLICT (employee_id, leave_type_id, year) DO NOTHING
                    RETURNING *;
                    """,
                    (employee_id, leave_type_id, year, quota, quota, carry_forwarded),
                )
                return cur.fetchone()

    @staticmethod
    def get_balance(employee_id, year):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT b.*, t.name AS leave_type_name, t.is_paid
                    FROM employee_leave_balance b
                    JOIN leave_types t ON b.leave_type_id=t.leave_type_id
                    WHERE employee_id=%s AND year=%s;
                    """,
                    (employee_id, year),
                )
                return cur.fetchall()

    @staticmethod
    def get_single_balance(employee_id, leave_type_id, year):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT b.*, t.name AS leave_type_name, t.is_paid
                    FROM employee_leave_balance b
                    JOIN leave_types t ON b.leave_type_id=t.leave_type_id
                    WHERE employee_id=%s AND b.leave_type_id=%s AND year=%s;
                    """,
                    (employee_id, leave_type_id, year),
                )
                return cur.fetchone()

    @staticmethod
    def update_balance_used_safe(employee_id, leave_type_id, year, used_days):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE employee_leave_balance
                    SET used = used + %s,
                        remaining = remaining - %s
                    WHERE employee_id=%s
                      AND leave_type_id=%s
                      AND year=%s
                      AND remaining >= %s
                    RETURNING *;
                    """,
                    (
                        used_days,
                        used_days,
                        employee_id,
                        leave_type_id,
                        year,
                        used_days,
                    ),
                )
                return cur.fetchone()


# ===============================================
#  LEAVE REQUESTS CRUD / BUSINESS LOGIC
# ===============================================
class LeaveRequestDB:

    # --------- VALIDATION HELPERS ---------

    @staticmethod
    def has_approved_leave(employee_id: int, dt: date) -> bool:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1
                    FROM leave_requests
                    WHERE employee_id = %s
                      AND status = 'approved'
                      AND start_date <= %s
                      AND end_date >= %s
                    LIMIT 1;
                    """,
                    (employee_id, dt, dt),
                )
                return cur.fetchone() is not None

    @staticmethod
    def has_overlapping_approved_leave(employee_id, start_date, end_date):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1
                    FROM leave_requests
                    WHERE employee_id=%s
                      AND status='approved'
                      AND start_date <= %s
                      AND end_date >= %s
                    LIMIT 1;
                    """,
                    (employee_id, end_date, start_date),
                )
                return cur.fetchone() is not None

    # --------- CRUD / ACTIONS ---------

    @staticmethod
    def apply_leave(employee_id, leave_type_id, start_date, end_date, total_days, reason):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO leave_requests
                    (employee_id, leave_type_id, start_date, end_date, total_days, reason)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *;
                    """,
                    (employee_id, leave_type_id, start_date, end_date, total_days, reason),
                )
                return cur.fetchone()

    @staticmethod
    def approve_leave_transaction(leave_id, manager_id):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                try:
                    # Lock leave
                    cur.execute(
                        """
                        SELECT *
                        FROM leave_requests
                        WHERE leave_id=%s
                        FOR UPDATE;
                        """,
                        (leave_id,),
                    )
                    leave = cur.fetchone()

                    if not leave:
                        raise Exception("Leave request not found")

                    if leave["status"] != "pending":
                        raise Exception(f"Leave is already {leave['status']}")

                    # Approve
                    cur.execute(
                        """
                        UPDATE leave_requests
                        SET status='approved',
                            approved_by=%s,
                            approved_on=NOW()
                        WHERE leave_id=%s
                        RETURNING *;
                        """,
                        (manager_id, leave_id),
                    )
                    leave = cur.fetchone()
                    year = leave["start_date"].year

                    # Check paid
                    cur.execute(
                        """
                        SELECT is_paid
                        FROM leave_types
                        WHERE leave_type_id=%s;
                        """,
                        (leave["leave_type_id"],),
                    )
                    lt = cur.fetchone()
                    is_paid = lt["is_paid"] if lt else True

                    if is_paid:
                        cur.execute(
                            """
                            UPDATE employee_leave_balance
                            SET used = used + %s,
                                remaining = remaining - %s
                            WHERE employee_id=%s
                              AND leave_type_id=%s
                              AND year=%s
                              AND remaining >= %s
                            RETURNING *;
                            """,
                            (
                                leave["total_days"],
                                leave["total_days"],
                                leave["employee_id"],
                                leave["leave_type_id"],
                                year,
                                leave["total_days"],
                            ),
                        )

                        if not cur.fetchone():
                            raise Exception("Insufficient leave balance")

                    # Insert history
                    cur.execute(
                        """
                        INSERT INTO leave_history
                        (employee_id, leave_type_id, start_date, end_date, total_days)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING *;
                        """,
                        (
                            leave["employee_id"],
                            leave["leave_type_id"],
                            leave["start_date"],
                            leave["end_date"],
                            leave["total_days"],
                        ),
                    )

                    history = cur.fetchone()
                    return {"leave": leave, "history": history}

                except Exception:
                    conn.rollback()
                    raise

    @staticmethod
    def reject_leave(leave_id, manager_id):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE leave_requests
                    SET status='rejected',
                        approved_by=%s,
                        approved_on=NOW()
                    WHERE leave_id=%s
                    RETURNING *;
                    """,
                    (manager_id, leave_id),
                )
                return cur.fetchone()

    @staticmethod
    def list_requests(employee_id=None):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if employee_id:
                    cur.execute(
                        """
                        SELECT lr.*, lt.name AS leave_type_name
                        FROM leave_requests lr
                        JOIN leave_types lt ON lr.leave_type_id = lt.leave_type_id
                        WHERE lr.employee_id=%s
                        ORDER BY lr.applied_on DESC;
                        """,
                        (employee_id,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT lr.*, lt.name AS leave_type_name
                        FROM leave_requests lr
                        JOIN leave_types lt ON lr.leave_type_id = lt.leave_type_id
                        ORDER BY lr.applied_on DESC;
                        """
                    )
                return cur.fetchall()

    @staticmethod
    def list_pending_requests():
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT lr.*, lt.name AS leave_type_name
                    FROM leave_requests lr
                    JOIN leave_types lt ON lr.leave_type_id = lt.leave_type_id
                    WHERE lr.status='pending'
                    ORDER BY lr.applied_on DESC;
                    """
                )
                return cur.fetchall()

    @staticmethod
    def update_leave_status_only(leave_id, status):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE leave_requests
                    SET status=%s,
                        approved_on=NOW()
                    WHERE leave_id=%s
                    RETURNING *;
                    """,
                    (status, leave_id),
                )
                return cur.fetchone()

    @staticmethod
    def get_employee_id_from_leave(leave_id):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT employee_id FROM leave_requests WHERE leave_id=%s;",
                    (leave_id,),
                )
                row = cur.fetchone()
                return row[0] if row else None


# ===============================================
#  LEAVE HISTORY / REPORTS
# ===============================================
class LeaveHistoryDB:

    @staticmethod
    def add_history(employee_id, leave_type_id, start_date, end_date, total_days):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO leave_history
                    (employee_id, leave_type_id, start_date, end_date, total_days)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *;
                    """,
                    (employee_id, leave_type_id, start_date, end_date, total_days),
                )
                return cur.fetchone()

    @staticmethod
    def get_history(employee_id):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT h.*, t.name AS leave_type_name, t.is_paid
                    FROM leave_history h
                    JOIN leave_types t ON h.leave_type_id=t.leave_type_id
                    WHERE employee_id=%s
                    ORDER BY recorded_on DESC;
                    """,
                    (employee_id,),
                )
                return cur.fetchall()

    @staticmethod
    def get_unpaid_leave_days(employee_id: int, year: int, month: int):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COALESCE(SUM(h.total_days), 0)
                    FROM leave_history h
                    JOIN leave_types t ON h.leave_type_id = t.leave_type_id
                    WHERE h.employee_id = %s
                      AND t.is_paid = FALSE
                      AND EXTRACT(YEAR FROM h.start_date) = %s
                      AND EXTRACT(MONTH FROM h.start_date) = %s;
                    """,
                    (employee_id, year, month),
                )
                row = cur.fetchone()
                return float(row[0]) if row and row[0] is not None else 0.0
