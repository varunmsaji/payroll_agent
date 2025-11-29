import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date

# -----------------------------------
# app/database/connection.py
# -----------------------------------

DB_PARAMS = {
    "dbname": "hrms_db",
    "user": "varun",
    "password": "varun@123",
    "host": "localhost",
    "port": 5432,
}

def get_connection():
    return psycopg2.connect(**DB_PARAMS)


# ===============================================
#  CREATE TABLES
# ===============================================
class LeaveTables:

    @staticmethod
    def create_tables():
        conn = get_connection()
        cur = conn.cursor()

        # 1. Leave Types
        cur.execute("""
            CREATE TABLE IF NOT EXISTS leave_types (
                leave_type_id SERIAL PRIMARY KEY,
                name VARCHAR(50) NOT NULL,
                code VARCHAR(10) UNIQUE NOT NULL,
                yearly_quota INT NOT NULL DEFAULT 0,
                is_paid BOOLEAN DEFAULT TRUE,
                carry_forward BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # 2. Leave Balances (assigned leave types)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS employee_leave_balance (
                id SERIAL PRIMARY KEY,
                employee_id INT NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
                leave_type_id INT NOT NULL REFERENCES leave_types(leave_type_id),
                year INT NOT NULL,
                total_quota INT NOT NULL,
                used INT DEFAULT 0,
                remaining INT NOT NULL,
                carry_forwarded INT DEFAULT 0,
                UNIQUE (employee_id, leave_type_id, year)
            );
        """)

        # 3. Leave Requests
        cur.execute("""
            CREATE TABLE IF NOT EXISTS leave_requests (
                leave_id SERIAL PRIMARY KEY,
                employee_id INT NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
                leave_type_id INT NOT NULL REFERENCES leave_types(leave_type_id),
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                total_days DECIMAL(5,2) NOT NULL,
                reason TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                applied_on TIMESTAMP DEFAULT NOW(),
                approved_by INT REFERENCES employees(employee_id),
                approved_on TIMESTAMP
            );
        """)

        # 4. Leave History
        cur.execute("""
            CREATE TABLE IF NOT EXISTS leave_history (
                id SERIAL PRIMARY KEY,
                employee_id INT NOT NULL REFERENCES employees(employee_id),
                leave_type_id INT NOT NULL REFERENCES leave_types(leave_type_id),
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                total_days DECIMAL(5,2) NOT NULL,
                recorded_on TIMESTAMP DEFAULT NOW()
            );
        """)

        conn.commit()
        conn.close()
        return "Leave tables created successfully"


# ===============================================
#  HELPER: EMPLOYEE SALARY (for payroll)
# ===============================================
class EmployeeSalaryDB:
    """
    Minimal helper assuming employees table has base_salary.
    Adjust column name if different.
    """

    @staticmethod
    def get_base_salary(employee_id: int):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT base_salary
            FROM employees
            WHERE employee_id=%s;
        """, (employee_id,))
        row = cur.fetchone()
        conn.close()
        return row  # { "base_salary": ... } or None


# ===============================================
#  LEAVE TYPES CRUD
# ===============================================
class LeaveTypeDB:

    @staticmethod
    def add_leave_type(name, code, yearly_quota=0, is_paid=True, carry_forward=True):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            INSERT INTO leave_types (name, code, yearly_quota, is_paid, carry_forward)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *;
        """, (name, code, yearly_quota, is_paid, carry_forward))

        res = cur.fetchone()
        conn.commit()
        conn.close()
        return res

    @staticmethod
    def get_leave_types():
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT * FROM leave_types ORDER BY leave_type_id;")
        rows = cur.fetchall()

        conn.close()
        return rows

    @staticmethod
    def get_leave_type(leave_type_id: int):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM leave_types WHERE leave_type_id=%s;", (leave_type_id,))
        row = cur.fetchone()
        conn.close()
        return row


# ===============================================
#  LEAVE BALANCE CRUD / VALIDATION
# ===============================================
class LeaveBalanceDB:

    @staticmethod
    def initialize_balance(employee_id, leave_type_id, year, quota, carry_forwarded=0):
        """
        Assigns a leave type to an employee for a year.
        """
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            INSERT INTO employee_leave_balance
            (employee_id, leave_type_id, year, total_quota, used, remaining, carry_forwarded)
            VALUES (%s, %s, %s, %s, 0, %s, %s)
            ON CONFLICT (employee_id, leave_type_id, year) DO NOTHING
            RETURNING *;
        """, (employee_id, leave_type_id, year, quota, quota, carry_forwarded))

        res = cur.fetchone()
        conn.commit()
        conn.close()
        return res

    @staticmethod
    def get_balance(employee_id, year):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT b.*, t.name as leave_type_name, t.is_paid
            FROM employee_leave_balance b
            JOIN leave_types t ON b.leave_type_id=t.leave_type_id
            WHERE employee_id=%s AND year=%s;
        """, (employee_id, year))

        rows = cur.fetchall()
        conn.close()
        return rows

    @staticmethod
    def get_single_balance(employee_id, leave_type_id, year):
        """
        Used to check if employee has this leave type assigned for given year.
        """
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT b.*, t.name as leave_type_name, t.is_paid
            FROM employee_leave_balance b
            JOIN leave_types t ON b.leave_type_id=t.leave_type_id
            WHERE employee_id=%s AND b.leave_type_id=%s AND year=%s;
        """, (employee_id, leave_type_id, year))

        row = cur.fetchone()
        conn.close()
        return row

    @staticmethod
    def update_balance_used_safe(employee_id, leave_type_id, year, used_days):
        """
        Safely updates used & remaining.
        Will FAIL if remaining < used_days (to avoid negative remaining).
        """
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            UPDATE employee_leave_balance
            SET used = used + %s,
                remaining = remaining - %s
            WHERE employee_id=%s
              AND leave_type_id=%s
              AND year=%s
              AND remaining >= %s
            RETURNING *;
        """, (used_days, used_days, employee_id, leave_type_id, year, used_days))

        res = cur.fetchone()
        conn.commit()
        conn.close()
        return res  # None if insufficient balance


# ===============================================
#  LEAVE REQUESTS CRUD / BUSINESS LOGIC
# ===============================================
class LeaveRequestDB:

    # --------- VALIDATION HELPERS ---------

    @staticmethod
    def has_overlapping_approved_leave(employee_id, start_date, end_date):
        """
        Check if employee already has an APPROVED leave overlapping this range.
        """
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT 1 FROM leave_requests
            WHERE employee_id=%s
              AND status='approved'
              AND (
                    (start_date <= %s AND end_date >= %s)
                  )
            LIMIT 1;
        """, (employee_id, end_date, start_date))

        exists = cur.fetchone()
        conn.close()
        return exists is not None

    # --------- CRUD / ACTIONS ---------

    @staticmethod
    def apply_leave(employee_id, leave_type_id, start_date, end_date, total_days, reason):
        """
        Creates a leave request (status = pending).
        Validation (has leave type, enough balance, overlap) should be done in service layer / router.
        """
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            INSERT INTO leave_requests
            (employee_id, leave_type_id, start_date, end_date, total_days, reason)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *;
        """, (employee_id, leave_type_id, start_date, end_date, total_days, reason))

        res = cur.fetchone()
        conn.commit()
        conn.close()
        return res

    @staticmethod
    def approve_leave_transaction(leave_id, manager_id):
        """
        ✅ Approves leave
        ✅ Deducts leave balance (only if paid)
        ✅ Inserts into leave history
        ✅ Fully transactional (commit/rollback safe)
        ✅ RealDictCursor compatible
        """
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # 1️⃣ Fetch leave and lock it FOR UPDATE
            cur.execute("""
                SELECT *
                FROM leave_requests
                WHERE leave_id=%s
                FOR UPDATE;
            """, (leave_id,))
            leave = cur.fetchone()

            if not leave:
                raise Exception("Leave request not found")

            if leave["status"] != "pending":
                raise Exception(f"Leave is already {leave['status']}")

            # 2️⃣ Approve leave request
            cur.execute("""
                UPDATE leave_requests
                SET status='approved',
                    approved_by=%s,
                    approved_on=NOW()
                WHERE leave_id=%s
                RETURNING *;
            """, (manager_id, leave_id))

            leave = cur.fetchone()

            year = leave["start_date"].year

            # 3️⃣ ✅ Check if leave type is PAID (FIXED)
            cur.execute("""
                SELECT is_paid 
                FROM leave_types 
                WHERE leave_type_id=%s;
            """, (leave["leave_type_id"],))

            lt = cur.fetchone()

            # ✅ FIX: Safe RealDictCursor access
            is_paid = lt["is_paid"] if lt and "is_paid" in lt else True

            # 4️⃣ ✅ Deduct balance ONLY if PAID
            if is_paid:
                cur.execute("""
                    UPDATE employee_leave_balance
                    SET used = used + %s,
                        remaining = remaining - %s
                    WHERE employee_id=%s
                    AND leave_type_id=%s
                    AND year=%s
                    AND remaining >= %s
                    RETURNING *;
                """, (
                    leave["total_days"],
                    leave["total_days"],
                    leave["employee_id"],
                    leave["leave_type_id"],
                    year,
                    leave["total_days"]
                ))

                balance = cur.fetchone()
                if not balance:
                    raise Exception("Insufficient leave balance or leave not assigned")

            # 5️⃣ ✅ Insert into leave history
            cur.execute("""
                INSERT INTO leave_history
                (employee_id, leave_type_id, start_date, end_date, total_days)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *;
            """, (
                leave["employee_id"],
                leave["leave_type_id"],
                leave["start_date"],
                leave["end_date"],
                leave["total_days"]
            ))

            history = cur.fetchone()

            # ✅ COMMIT ALL CHANGES
            conn.commit()

            return {
                "leave": leave,
                "history": history
            }

        except Exception as e:
            conn.rollback()
            raise e

        finally:
            conn.close()


    @staticmethod
    def reject_leave(leave_id, manager_id):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            UPDATE leave_requests
            SET status='rejected',
                approved_by=%s,
                approved_on=NOW()
            WHERE leave_id=%s
            RETURNING *;
        """, (manager_id, leave_id))

        res = cur.fetchone()
        conn.commit()
        conn.close()
        return res

    @staticmethod
    def list_requests(employee_id=None):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        if employee_id:
            cur.execute("""
                SELECT lr.*, lt.name AS leave_type_name
                FROM leave_requests lr
                JOIN leave_types lt ON lr.leave_type_id = lt.leave_type_id
                WHERE lr.employee_id=%s
                ORDER BY lr.applied_on DESC;
            """, (employee_id,))
        else:
            cur.execute("""
                SELECT lr.*, lt.name AS leave_type_name
                FROM leave_requests lr
                JOIN leave_types lt ON lr.leave_type_id = lt.leave_type_id
                ORDER BY lr.applied_on DESC;
            """)

        rows = cur.fetchall()
        conn.close()
        return rows

    @staticmethod
    def list_pending_requests():
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT lr.*, lt.name AS leave_type_name
            FROM leave_requests lr
            JOIN leave_types lt ON lr.leave_type_id = lt.leave_type_id
            WHERE lr.status='pending'
            ORDER BY lr.applied_on DESC;
        """)
        rows = cur.fetchall()
        conn.close()
        return rows
    

    @staticmethod
    def update_leave_status_only(leave_id, status):
        """
        ✅ Used by Workflow Engine on FINAL approval/rejection
        """
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            UPDATE leave_requests
            SET status=%s,
                approved_on=NOW()
            WHERE leave_id=%s
            RETURNING *;
        """, (status, leave_id))

        row = cur.fetchone()
        conn.commit()
        conn.close()
        return row


    @staticmethod
    def get_employee_id_from_leave(leave_id):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT employee_id
            FROM leave_requests
            WHERE leave_id=%s;
        """, (leave_id,))

        row = cur.fetchone()
        conn.close()
        return row[0] if row else None



# ===============================================
#  LEAVE HISTORY / REPORTS
# ===============================================
class LeaveHistoryDB:

    @staticmethod
    def add_history(employee_id, leave_type_id, start_date, end_date, total_days):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            INSERT INTO leave_history
            (employee_id, leave_type_id, start_date, end_date, total_days)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *;
        """, (employee_id, leave_type_id, start_date, end_date, total_days))

        res = cur.fetchone()
        conn.commit()
        conn.close()
        return res

    @staticmethod
    def get_history(employee_id):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT h.*, t.name AS leave_type_name, t.is_paid
            FROM leave_history h
            JOIN leave_types t ON h.leave_type_id=t.leave_type_id
            WHERE employee_id=%s
            ORDER BY recorded_on DESC;
        """, (employee_id,))

        rows = cur.fetchall()
        conn.close()
        return rows

    @staticmethod
    def get_unpaid_leave_days(employee_id: int, year: int, month: int):
        """
        Sum of unpaid leave days from history for a given month/year.
        Uses leave_types.is_paid = FALSE
        """
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT COALESCE(SUM(h.total_days), 0) AS unpaid_days
            FROM leave_history h
            JOIN leave_types t ON h.leave_type_id = t.leave_type_id
            WHERE h.employee_id = %s
              AND t.is_paid = FALSE
              AND EXTRACT(YEAR FROM h.start_date) = %s
              AND EXTRACT(MONTH FROM h.start_date) = %s;
        """, (employee_id, year, month))

        row = cur.fetchone()
        conn.close()
        return float(row[0]) if row and row[0] is not None else 0.0


if __name__ == "__main__":
    print("Creating leave tables...")
    LeaveTables.create_tables()
    print("Done!")
