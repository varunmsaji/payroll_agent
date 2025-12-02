import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
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

    conn.commit()
    conn.close()


# ================================
# ✅ WORKFLOW CRUD
# ================================
def create_workflow(name, module, steps):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "INSERT INTO workflows (name, module) VALUES (%s,%s) RETURNING id;",
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
# ✅ ✅ ✅ MISSING SETTINGS FUNCTIONS (FIX)
# ================================
def get_all_workflows():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM workflows ORDER BY created_at DESC;")
    rows = cur.fetchall()

    conn.close()
    return rows


def activate_workflow(workflow_id):
    conn = get_connection()
    cur = conn.cursor()

    # Deactivate all for same module first (only one active allowed)
    cur.execute("""
        UPDATE workflows SET is_active = FALSE
        WHERE module = (SELECT module FROM workflows WHERE id = %s);
    """, (workflow_id,))

    # Activate selected workflow
    cur.execute("""
        UPDATE workflows SET is_active = TRUE WHERE id = %s;
    """, (workflow_id,))

    conn.commit()
    conn.close()
    return True


def deactivate_workflow(workflow_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE workflows SET is_active = FALSE WHERE id = %s;
    """, (workflow_id,))

    conn.commit()
    conn.close()
    return True


# ================================
# ✅ ROLE → USER RESOLVER
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
# ✅ AUTO START WORKFLOW
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
        raise Exception(f"No approver found for role: {first_step['role']}")

    cur.execute("""
        INSERT INTO approval_logs
        (module, request_id, workflow_id, step_order, approver_id, status)
        VALUES (%s,%s,%s,1,%s,'pending')
    """, (module, request_id, workflow_id, approver_id))

    cur.execute("""
        INSERT INTO request_status (module, request_id, status)
        VALUES (%s,%s,'pending')
        ON CONFLICT (module, request_id)
        DO UPDATE SET status='pending'
    """, (module, request_id))

    conn.commit()
    conn.close()

    return {
        "message": "Workflow started",
        "assigned_to": approver_id,
        "role": first_step["role"]
    }


# ================================
# ✅ FINAL STATUS VIEW
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
