# app/database/workflow_db.py

from datetime import datetime
from typing import Optional

from psycopg2.extras import RealDictCursor

from app.database.connection import get_connection
from app.database.employee_db import EmployeeDB
from app.database.leave_database import LeaveRequestDB


# ================================
# ✅ TABLE CREATION
# ================================
def create_workflow_tables():
    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
            CREATE TABLE IF NOT EXISTS workflows (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                module VARCHAR(50) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS workflow_steps (
                id SERIAL PRIMARY KEY,
                workflow_id INT NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
                step_order INT NOT NULL,
                role VARCHAR(50) NOT NULL,
                is_final BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (workflow_id, step_order)
            );

            CREATE TABLE IF NOT EXISTS approval_logs (
                id SERIAL PRIMARY KEY,
                module VARCHAR(50) NOT NULL,
                request_id INT NOT NULL,
                workflow_id INT NOT NULL REFERENCES workflows(id),
                step_order INT NOT NULL,
                approver_id INT NOT NULL,
                status VARCHAR(20) CHECK (status IN ('pending','approved','rejected')),
                acted_at TIMESTAMP,
                remarks TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (module, request_id, step_order)
            );

            CREATE TABLE IF NOT EXISTS request_status (
                id SERIAL PRIMARY KEY,
                module VARCHAR(50) NOT NULL,
                request_id INT NOT NULL,
                status VARCHAR(20) CHECK (status IN ('pending','approved','rejected')),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (module, request_id)
            );
            """
            )

            # DB-level safety: only one active workflow per module
            cur.execute(
                """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = 'idx_one_active_workflow_per_module'
                ) THEN
                    CREATE UNIQUE INDEX idx_one_active_workflow_per_module
                    ON workflows(module)
                    WHERE is_active = TRUE;
                END IF;
            END$$;
            """
            )


# ================================
# ✅ WORKFLOW CREATION
# ================================
def create_workflow(name, module, steps):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute(
                """
                INSERT INTO workflows (name, module, is_active)
                VALUES (%s,%s,FALSE)
                RETURNING id;
                """,
                (name, module),
            )
            workflow_id = cur.fetchone()["id"]

            for step in steps:
                cur.execute(
                    """
                    INSERT INTO workflow_steps
                    (workflow_id, step_order, role, is_final)
                    VALUES (%s,%s,%s,%s);
                    """,
                    (workflow_id, step["step_order"], step["role"], step["is_final"]),
                )

            return workflow_id


# ================================
# ✅ FETCH / LIST
# ================================
def get_active_workflow(module):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT *
                FROM workflows
                WHERE module=%s AND is_active=TRUE
                ORDER BY id DESC
                LIMIT 1;
                """,
                (module,),
            )
            return cur.fetchone()


def get_all_workflows():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM workflows ORDER BY created_at DESC;")
            return cur.fetchall()


# ================================
# ✅ ACTIVATE / DEACTIVATE
# ================================
def activate_workflow(workflow_id):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("SELECT module FROM workflows WHERE id=%s;", (workflow_id,))
            row = cur.fetchone()
            if not row:
                raise Exception("Workflow not found")

            module = row["module"]

            cur.execute("UPDATE workflows SET is_active=FALSE WHERE module=%s;", (module,))
            cur.execute("UPDATE workflows SET is_active=TRUE WHERE id=%s;", (workflow_id,))

            return True


def deactivate_workflow(workflow_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE workflows SET is_active=FALSE WHERE id=%s;", (workflow_id,))
            return True


# ================================
# ✅ DELETE WORKFLOW (SAFE)
# ================================
def delete_workflow(workflow_id: int):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute(
                "SELECT COUNT(*) AS cnt FROM approval_logs WHERE workflow_id=%s;",
                (workflow_id,),
            )
            if cur.fetchone()["cnt"] > 0:
                raise Exception("Cannot delete workflow with approval history")

            cur.execute("DELETE FROM workflow_steps WHERE workflow_id=%s;", (workflow_id,))
            cur.execute("DELETE FROM workflows WHERE id=%s;", (workflow_id,))
            return True


# ================================
# ✅ ROLE → APPROVER
# ================================
def resolve_approver_by_role(role, employee_id):
    role = role.lower()

    if role == "manager":
        return EmployeeDB.get_manager_id(employee_id)
    if role == "hr":
        return EmployeeDB.get_hr_user()
    if role == "finance":
        return EmployeeDB.get_finance_head()
    if role == "director":
        return EmployeeDB.get_director()

    return None


# ================================
# ✅ WORKFLOW START
# ================================
def start_workflow(module, request_id, workflow_id, employee_id):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute(
                """
                SELECT *
                FROM workflow_steps
                WHERE workflow_id=%s AND step_order=1;
                """,
                (workflow_id,),
            )
            first_step = cur.fetchone()
            if not first_step:
                raise Exception("No workflow steps defined")

            approver_id = resolve_approver_by_role(first_step["role"], employee_id)
            if not approver_id:
                raise Exception("No approver found")

            cur.execute(
                """
                INSERT INTO approval_logs
                (module, request_id, workflow_id, step_order, approver_id, status)
                VALUES (%s,%s,%s,1,%s,'pending');
                """,
                (module, request_id, workflow_id, approver_id),
            )

            cur.execute(
                """
                INSERT INTO request_status (module, request_id, status)
                VALUES (%s,%s,'pending')
                ON CONFLICT (module, request_id)
                DO UPDATE SET status='pending', updated_at=NOW();
                """,
                (module, request_id),
            )

            return {
                "message": "Workflow started",
                "assigned_to": approver_id,
                "role": first_step["role"],
            }


# ================================
# ✅ STATUS / UI
# ================================
def get_workflow_status(module, request_id):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute(
                "SELECT * FROM request_status WHERE module=%s AND request_id=%s;",
                (module, request_id),
            )
            status = cur.fetchone()

            cur.execute(
                """
                SELECT *
                FROM approval_logs
                WHERE module=%s AND request_id=%s
                ORDER BY step_order;
                """,
                (module, request_id),
            )
            history = cur.fetchall()

            return {"status": status, "history": history}
