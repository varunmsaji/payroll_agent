import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Optional

from app.database.employee_db import EmployeeDB
from app.database.leave_database import LeaveRequestDB


DB_PARAMS = {
    "dbname": "hrms_db",
    "user": "varun",
    "password": "varun@123",
    "host": "localhost",
    "port": 5432,
}


def get_connection():
    return psycopg2.connect(**DB_PARAMS)


# ================================
# ✅ TABLE CREATION
# ================================
def create_workflow_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
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
    """)

    # ✅ DB-LEVEL SAFETY: Only ONE active workflow per module
    cur.execute("""
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
    """)

    conn.commit()
    conn.close()


# ================================
# ✅ WORKFLOW CREATION
# ================================
def create_workflow(name, module, steps):
    """
    Create a new workflow. New workflows start INACTIVE.
    Admin must explicitly activate them.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "INSERT INTO workflows (name, module, is_active) VALUES (%s,%s,FALSE) RETURNING id;",
        (name, module)
    )
    workflow_id = cur.fetchone()["id"]

    for step in steps:
        cur.execute("""
        INSERT INTO workflow_steps (workflow_id, step_order, role, is_final)
        VALUES (%s,%s,%s,%s)
        """, (workflow_id, step["step_order"], step["role"], step["is_final"]))

    conn.commit()
    conn.close()
    return workflow_id


# ================================
# ✅ ACTIVE WORKFLOW FETCH
# ================================
def get_active_workflow(module):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT * FROM workflows
        WHERE module=%s AND is_active=true
        ORDER BY id DESC LIMIT 1
    """, (module,))

    row = cur.fetchone()
    conn.close()
    return row


# ================================
# ✅ ADMIN LISTING
# ================================
def get_all_workflows():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM workflows ORDER BY created_at DESC;")
    rows = cur.fetchall()

    conn.close()
    return rows


# ================================
# ✅ ACTIVATE / DEACTIVATE
# ================================
def activate_workflow(workflow_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT module FROM workflows WHERE id = %s;", (workflow_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise Exception("Workflow not found")

    module = row["module"]

    # Deactivate all workflows for same module
    cur.execute("""
        UPDATE workflows SET is_active = FALSE
        WHERE module = %s;
    """, (module,))

    # Activate selected workflow
    cur.execute("""
        UPDATE workflows SET is_active = TRUE
        WHERE id = %s;
    """, (workflow_id,))

    conn.commit()
    conn.close()
    return True


def deactivate_workflow(workflow_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("UPDATE workflows SET is_active = FALSE WHERE id = %s;", (workflow_id,))
    conn.commit()
    conn.close()
    return True


# ================================
# ✅ DELETE WORKFLOW (NO HISTORY)
# ================================
def delete_workflow(workflow_id: int):
    """
    Delete a workflow only if it has NO approval history.
    Prevents breaking audit logs.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Check if any approval_logs exist for this workflow
    cur.execute("""
        SELECT COUNT(*) AS cnt
        FROM approval_logs
        WHERE workflow_id = %s;
    """, (workflow_id,))
    row = cur.fetchone()
    if row and row["cnt"] > 0:
        conn.close()
        raise Exception("Cannot delete workflow with existing approval history")

    # Safe to delete steps + workflow
    cur.execute("DELETE FROM workflow_steps WHERE workflow_id = %s;", (workflow_id,))
    cur.execute("DELETE FROM workflows WHERE id = %s;", (workflow_id,))

    conn.commit()
    conn.close()
    return True


# ================================
# ✅ ROLE → APPROVER RESOLUTION
# ================================
def resolve_approver_by_role(role, employee_id):
    role = role.lower()

    if role == "manager":
        return EmployeeDB.get_manager_id(employee_id)
    elif role == "hr":
        return EmployeeDB.get_hr_user()
    elif role == "finance":
        return EmployeeDB.get_finance_head()
    elif role == "director":
        return EmployeeDB.get_director()

    return None


# ================================
# ✅ START WORKFLOW
# ================================
def start_workflow(module, request_id, workflow_id, employee_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT * FROM workflow_steps
        WHERE workflow_id=%s AND step_order=1
    """, (workflow_id,))
    first_step = cur.fetchone()

    if not first_step:
        conn.close()
        raise Exception("No workflow steps found")

    approver_id = resolve_approver_by_role(first_step["role"], employee_id)

    if not approver_id:
        conn.close()
        raise Exception("No approver found for role")

    cur.execute("""
        INSERT INTO approval_logs
        (module, request_id, workflow_id, step_order, approver_id, status)
        VALUES (%s,%s,%s,1,%s,'pending')
    """, (module, request_id, workflow_id, approver_id))

    cur.execute("""
        INSERT INTO request_status (module, request_id, status)
        VALUES (%s,%s,'pending')
        ON CONFLICT (module, request_id)
        DO UPDATE SET status='pending', updated_at = NOW()
    """, (module, request_id))

    conn.commit()
    conn.close()

    return {
        "message": "Workflow started",
        "assigned_to": approver_id,
        "role": first_step["role"]
    }


# ================================
# ✅ WORKFLOW STATUS
# ================================
def get_workflow_status(module, request_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT * FROM request_status
        WHERE module=%s AND request_id=%s
    """, (module, request_id))
    status = cur.fetchone()

    cur.execute("""
        SELECT * FROM approval_logs
        WHERE module=%s AND request_id=%s
        ORDER BY step_order
    """, (module, request_id))
    history = cur.fetchall()

    conn.close()
    return {"status": status, "history": history}


# ================================
# ✅ WORKFLOW DETAILS FOR UI
# ================================
def get_workflow_by_id(workflow_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM workflows WHERE id = %s;", (workflow_id,))
    wf = cur.fetchone()
    if not wf:
        conn.close()
        return None

    cur.execute("""
        SELECT id, workflow_id, step_order, role, is_final
        FROM workflow_steps
        WHERE workflow_id = %s
        ORDER BY step_order
    """, (workflow_id,))
    steps = cur.fetchall()

    conn.close()
    return {"workflow": wf, "steps": steps}


def get_active_workflow_with_steps(module: str):
    wf = get_active_workflow(module)
    if not wf:
        return None
    return get_workflow_by_id(wf["id"])


# ================================
# ✅ UPDATE WORKFLOW (PY 3.8 SAFE)
# ================================
def update_workflow(workflow_id: int, name: Optional[str], steps):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM workflows WHERE id = %s;", (workflow_id,))
    wf = cur.fetchone()

    if not wf:
        conn.close()
        raise Exception("Workflow not found")

    if wf["is_active"]:
        conn.close()
        raise Exception("Cannot edit an active workflow. Deactivate first.")

    if name:
        cur.execute(
            "UPDATE workflows SET name = %s WHERE id = %s;",
            (name, workflow_id)
        )

    cur.execute("DELETE FROM workflow_steps WHERE workflow_id = %s;", (workflow_id,))

    for step in steps:
        cur.execute("""
            INSERT INTO workflow_steps (workflow_id, step_order, role, is_final)
            VALUES (%s,%s,%s,%s)
        """, (workflow_id, step["step_order"], step["role"], step["is_final"]))

    conn.commit()
    conn.close()
    return True


# ================================
# ✅ APPROVER INBOX
# ================================
def get_pending_for_approver(approver_id: int):
    """
    Returns all pending approvals assigned to this approver.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT 
            al.id,
            al.module,
            al.request_id,
            al.workflow_id,
            al.step_order,
            al.status,
            al.created_at,
            w.name AS workflow_name,
            w.module AS workflow_module
        FROM approval_logs al
        JOIN workflows w ON al.workflow_id = w.id
        WHERE al.approver_id = %s
          AND al.status = 'pending'
        ORDER BY al.created_at DESC;
    """, (approver_id,))

    rows = cur.fetchall()
    conn.close()
    return rows


# ================================
# ✅ APPROVE / REJECT WITH SECURITY
# ================================
def approve_step(module: str, request_id: int, approver_id: int, remarks: str = ""):
    """
    Approve the current pending step for this module + request.
    Ensures the caller is the assigned approver.
    Creates next step if not final; else closes workflow.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get current pending step
    cur.execute("""
        SELECT * FROM approval_logs
        WHERE module=%s AND request_id=%s AND status='pending'
        ORDER BY step_order ASC
        LIMIT 1;
    """, (module, request_id))
    current = cur.fetchone()

    if not current:
        conn.close()
        raise Exception("No pending step found for this request")

    if current["approver_id"] != approver_id:
        conn.close()
        raise Exception("You are not the assigned approver for this step")

    # Mark current step as approved
    cur.execute("""
        UPDATE approval_logs
        SET status='approved', acted_at=NOW(), remarks=%s
        WHERE id=%s;
    """, (remarks, current["id"]))

    # Check if this step is final
    cur.execute("""
        SELECT is_final FROM workflow_steps
        WHERE workflow_id=%s AND step_order=%s;
    """, (current["workflow_id"], current["step_order"]))
    step_row = cur.fetchone()
    is_final = bool(step_row["is_final"]) if step_row else False

    if is_final:
        # Mark request as approved
        cur.execute("""
            UPDATE request_status
            SET status='approved', updated_at=NOW()
            WHERE module=%s AND request_id=%s;
        """, (module, request_id))

        # Module-specific handling
        if module == "leave":
            # Update leave request status (uses your existing DB function)
            LeaveRequestDB.update_leave_status_only(request_id, "approved")

        conn.commit()
        conn.close()

        return {
            "done": True,
            "final": True,
            "message": "Request fully approved"
        }

    # Not final → create next step
    next_step_order = current["step_order"] + 1

    cur.execute("""
        SELECT * FROM workflow_steps
        WHERE workflow_id=%s AND step_order=%s;
    """, (current["workflow_id"], next_step_order))
    next_step = cur.fetchone()

    if not next_step:
        # No next step defined, treat as final anyway
        cur.execute("""
            UPDATE request_status
            SET status='approved', updated_at=NOW()
            WHERE module=%s AND request_id=%s;
        """, (module, request_id))

        if module == "leave":
            LeaveRequestDB.update_leave_status_only(request_id, "approved")

        conn.commit()
        conn.close()

        return {
            "done": True,
            "final": True,
            "message": "Request approved (no further steps defined)"
        }

    # Resolve next approver (for HR/Finance/Director employee_id isn't needed)
    next_approver_id = resolve_approver_by_role(next_step["role"], None)

    if not next_approver_id:
        conn.close()
        raise Exception("No approver found for next step role")

    # Insert next pending approval
    cur.execute("""
        INSERT INTO approval_logs
        (module, request_id, workflow_id, step_order, approver_id, status)
        VALUES (%s,%s,%s,%s,%s,'pending')
    """, (module, request_id, current["workflow_id"], next_step_order, next_approver_id))

    conn.commit()
    conn.close()

    return {
        "done": False,
        "final": False,
        "next_step_order": next_step_order,
        "next_approver_id": next_approver_id,
        "next_role": next_step["role"]
    }


def reject_step(module: str, request_id: int, approver_id: int, remarks: str = ""):
    """
    Reject the current pending step.
    Ensures the caller is the assigned approver.
    Marks the entire request as rejected.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT * FROM approval_logs
        WHERE module=%s AND request_id=%s AND status='pending'
        ORDER BY step_order ASC
        LIMIT 1;
    """, (module, request_id))
    current = cur.fetchone()

    if not current:
        conn.close()
        raise Exception("No pending step found for this request")

    if current["approver_id"] != approver_id:
        conn.close()
        raise Exception("You are not the assigned approver for this step")

    cur.execute("""
        UPDATE approval_logs
        SET status='rejected', acted_at=NOW(), remarks=%s
        WHERE id=%s;
    """, (remarks, current["id"]))

    cur.execute("""
        UPDATE request_status
        SET status='rejected', updated_at=NOW()
        WHERE module=%s AND request_id=%s;
    """, (module, request_id))

    if module == "leave":
        LeaveRequestDB.update_leave_status_only(request_id, "rejected")

    conn.commit()
    conn.close()

    return True
