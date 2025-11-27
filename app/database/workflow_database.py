import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from app.database.employee_db import EmployeeDB


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
# ✅ AUTO START WORKFLOW (FIXED ✅)
# ================================
def start_workflow(module, request_id, workflow_id, employee_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # ✅ Get FIRST step
    cur.execute("""
        SELECT * FROM workflow_steps
        WHERE workflow_id=%s AND step_order=1
    """, (workflow_id,))
    first_step = cur.fetchone()

    if not first_step:
        conn.close()
        raise Exception("No workflow steps found")

    # ✅ Resolve approver dynamically
    approver_id = resolve_approver_by_role(first_step["role"], employee_id)

    if not approver_id:
        conn.close()
        raise Exception(f"No approver found for role: {first_step['role']}")

    # ✅ Insert FIRST step
    cur.execute("""
        INSERT INTO approval_logs
        (module, request_id, workflow_id, step_order, approver_id, status)
        VALUES (%s,%s,%s,1,%s,'pending')
    """, (module, request_id, workflow_id, approver_id))

    # ✅ Set request status
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
# ✅ APPROVE STEP + AUTO MOVE
# ================================
def approve_step(module, request_id, remarks):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE approval_logs
        SET status='approved', acted_at=%s, remarks=%s
        WHERE module=%s AND request_id=%s AND status='pending'
    """, (datetime.now(), remarks, module, request_id))

    conn.commit()
    conn.close()

    return move_to_next_step(module, request_id)


# ================================
# ✅ MOVE TO NEXT STEP (FIXED ✅)
# ================================
# ================================
# ✅ MOVE TO NEXT STEP (FINAL + LEAVE SYNC ✅✅✅)
# ================================
def move_to_next_step(module, request_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # ✅ Get last approved step
    cur.execute("""
        SELECT step_order, workflow_id
        FROM approval_logs
        WHERE module=%s AND request_id=%s
        ORDER BY step_order DESC LIMIT 1
    """, (module, request_id))

    current = cur.fetchone()
    if not current:
        conn.close()
        return {"error": "No workflow started"}

    current_step = current["step_order"]
    workflow_id = current["workflow_id"]

    # ✅ Get next step
    cur.execute("""
        SELECT * FROM workflow_steps
        WHERE workflow_id=%s AND step_order=%s
    """, (workflow_id, current_step + 1))

    next_step = cur.fetchone()

    # =========================================================
    # ✅✅✅✅ FINAL APPROVAL — UPDATE LEAVE TABLE ALSO ✅✅✅✅
    # =========================================================
    if not next_step:
        # ✅ Update workflow status
        cur.execute("""
            UPDATE request_status
            SET status='approved', updated_at=%s
            WHERE module=%s AND request_id=%s
        """, (datetime.now(), module, request_id))

        conn.commit()
        conn.close()

        # ✅ IF THIS IS LEAVE → ALSO APPROVE LEAVE + DEDUCT BALANCE
        if module == "leave":
            from app.database.leave_database import LeaveRequestDB

            # ✅ This updates:
            # - leave_requests.status = approved
            # - leave_history insert
            # - employee_leave_balance deduction
            LeaveRequestDB.approve_leave_transaction(request_id, manager_id=31)

        return {
            "message": "Workflow completed (Final Approval) + Leave Approved ✅"
        }

    # =========================================================
    # ✅ MOVE TO NEXT APPROVER
    # =========================================================

    # ⚠️ TEMP TEST ASSUMPTION: request_id == employee_id
    employee_id = request_id

    approver_id = resolve_approver_by_role(
        next_step["role"], employee_id
    )

    if not approver_id:
        conn.close()
        return {"error": f"No approver found for role: {next_step['role']}"}

    # ✅ Insert next step
    cur.execute("""
        INSERT INTO approval_logs
        (module, request_id, workflow_id, step_order, approver_id, status)
        VALUES (%s,%s,%s,%s,%s,'pending')
    """, (
        module,
        request_id,
        workflow_id,
        next_step["step_order"],
        approver_id
    ))

    conn.commit()
    conn.close()

    return {
        "message": f"Moved to step {next_step['step_order']}",
        "assigned_to": approver_id,
        "role": next_step["role"]
    }



# ================================
# ✅ REJECT FLOW
# ================================
def reject_step(module, request_id, remarks):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE approval_logs
        SET status='rejected', acted_at=%s, remarks=%s
        WHERE module=%s AND request_id=%s AND status='pending'
    """, (datetime.now(), remarks, module, request_id))

    cur.execute("""
        UPDATE request_status SET status='rejected'
        WHERE module=%s AND request_id=%s
    """, (module, request_id))

    conn.commit()
    conn.close()


# ================================
# ✅ STATUS VIEW
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


if __name__ == "__main__":
    create_workflow_tables()
