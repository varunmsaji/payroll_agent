# app/database/workflow_db.py

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

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
    cur.execute(
        "SELECT * FROM workflows WHERE module=%s AND is_active=true ORDER BY id DESC LIMIT 1",
        (module,)
    )
    row = cur.fetchone()
    conn.close()
    return row


def get_workflow_steps(workflow_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT * FROM workflow_steps WHERE workflow_id=%s ORDER BY step_order",
        (workflow_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ================================
# ✅ APPROVAL ENGINE
# ================================
def start_workflow(module, request_id, workflow_id, approver_id):
    conn = get_connection()
    cur = conn.cursor()

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


def get_pending_step(module, request_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
    SELECT * FROM approval_logs
    WHERE module=%s AND request_id=%s AND status='pending'
    ORDER BY step_order LIMIT 1
    """, (module, request_id))

    row = cur.fetchone()
    conn.close()
    return row


def approve_step(module, request_id, remarks):
    conn = get_connection()
    cur = conn.cursor()

    # ✅ Approve current step
    cur.execute("""
        UPDATE approval_logs
        SET status='approved', acted_at=%s, remarks=%s
        WHERE module=%s AND request_id=%s AND status='pending'
    """, (datetime.now(), remarks, module, request_id))

    conn.commit()
    conn.close()

    # ✅ AUTO MOVE TO NEXT STEP
    return move_to_next_step(module, request_id)


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


def get_workflow_status(module, request_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM request_status WHERE module=%s AND request_id=%s",
                (module, request_id))
    status = cur.fetchone()

    cur.execute("""
    SELECT * FROM approval_logs
    WHERE module=%s AND request_id=%s
    ORDER BY step_order
    """, (module, request_id))
    history = cur.fetchall()

    conn.close()
    return {"status": status, "history": history}



def move_to_next_step(module, request_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1️⃣ Get already approved highest step
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

    # 2️⃣ Get next workflow step
    cur.execute("""
        SELECT * FROM workflow_steps
        WHERE workflow_id=%s AND step_order=%s
    """, (workflow_id, current_step + 1))

    next_step = cur.fetchone()

    # ✅ If no next step → workflow complete
    if not next_step:
        cur.execute("""
            UPDATE request_status
            SET status='approved', updated_at=%s
            WHERE module=%s AND request_id=%s
        """, (datetime.now(), module, request_id))

        conn.commit()
        conn.close()
        return {"message": "Workflow completed"}

    # 3️⃣ Insert next pending step (TEMP approver_id=1 for now)
    cur.execute("""
        INSERT INTO approval_logs
        (module, request_id, workflow_id, step_order, approver_id, status)
        VALUES (%s,%s,%s,%s,%s,'pending')
    """, (
        module,
        request_id,
        workflow_id,
        next_step["step_order"],
        1  # ✅ TEMP HARD-CODED — will be dynamic later
    ))

    conn.commit()
    conn.close()
    return {"message": f"Moved to step {next_step['step_order']}"}


if __name__ == "__main__":
    create_workflow_tables()