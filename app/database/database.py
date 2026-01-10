import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================
# DATABASE CONFIG
# ============================================================
DB_PARAMS = {
    "dbname": "hrms_db",
    "user": "varun",
    "password": "varun@123",
    "host": "localhost",
    "port": 5432,
}

# ============================================================
# CONNECTOR
# ============================================================
def get_connection():
    return psycopg2.connect(**DB_PARAMS)

# ============================================================
# CREATE ALL TABLES
# ============================================================
def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    # ============================================================
    # EMPLOYEES
    # ============================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        employee_id SERIAL PRIMARY KEY,
        first_name VARCHAR(100),
        last_name VARCHAR(100),
        email VARCHAR(255) UNIQUE,
        phone VARCHAR(20),
        designation VARCHAR(100),
        department VARCHAR(100),
        date_of_joining DATE,
        base_salary NUMERIC(10,2) NOT NULL,
        manager_id INT REFERENCES employees(employee_id),
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    # ============================================================
    # SHIFTS
    # ============================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS shifts (
        shift_id SERIAL PRIMARY KEY,
        shift_name VARCHAR(100) NOT NULL,
        start_time TIME NOT NULL,
        end_time TIME NOT NULL,
        is_night_shift BOOLEAN DEFAULT FALSE,
        break_start TIME,
        break_end TIME,
        break_minutes INT DEFAULT 0,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    # ============================================================
    # EMPLOYEE SHIFTS
    # ============================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employee_shifts (
        id SERIAL PRIMARY KEY,
        employee_id INT REFERENCES employees(employee_id) ON DELETE CASCADE,
        shift_id INT REFERENCES shifts(shift_id) ON DELETE SET NULL,
        effective_from DATE NOT NULL,
        effective_to DATE,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    # ============================================================
    # ATTENDANCE EVENTS (RAW)
    # ============================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance_events (
        event_id SERIAL PRIMARY KEY,
        employee_id INT REFERENCES employees(employee_id) ON DELETE CASCADE,
        event_type VARCHAR(20) NOT NULL,
        event_time TIMESTAMP NOT NULL,
        source VARCHAR(40) DEFAULT 'manual',
        meta JSONB,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    # ============================================================
    # ATTENDANCE (PROCESSED)
    # ============================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        attendance_id SERIAL PRIMARY KEY,
        employee_id INT REFERENCES employees(employee_id) ON DELETE CASCADE,
        shift_id INT,
        date DATE NOT NULL,
        check_in TIMESTAMP,
        check_out TIMESTAMP,
        total_hours NUMERIC(5,2),
        net_hours NUMERIC(5,2),
        break_minutes INT DEFAULT 0,
        overtime_minutes INT DEFAULT 0,
        late_minutes INT DEFAULT 0,
        early_exit_minutes INT DEFAULT 0,
        is_late BOOLEAN DEFAULT FALSE,
        is_early_checkout BOOLEAN DEFAULT FALSE,
        is_overtime BOOLEAN DEFAULT FALSE,
        is_weekend BOOLEAN DEFAULT FALSE,
        is_holiday BOOLEAN DEFAULT FALSE,
        is_night_shift BOOLEAN DEFAULT FALSE,
        status VARCHAR(20) DEFAULT 'present',
        is_payroll_locked BOOLEAN DEFAULT FALSE,
        locked_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(employee_id, date)
    );
    """)

    # ============================================================
    # HOLIDAYS
    # ============================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS holidays (
        holiday_id SERIAL PRIMARY KEY,
        holiday_date DATE UNIQUE,
        name VARCHAR(100),
        is_optional BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    # ============================================================
    # SALARY STRUCTURE
    # ============================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS salary_structure (
        id SERIAL PRIMARY KEY,
        employee_id INT REFERENCES employees(employee_id) ON DELETE CASCADE,
        basic NUMERIC(10,2) NOT NULL,
        hra NUMERIC(10,2) NOT NULL,
        allowances NUMERIC(10,2) DEFAULT 0,
        deductions NUMERIC(10,2) DEFAULT 0,
        effective_from DATE NOT NULL,
        effective_to DATE,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    # ============================================================
    # PAYROLL
    # ============================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payroll (
        payroll_id SERIAL PRIMARY KEY,
        employee_id INT REFERENCES employees(employee_id) ON DELETE CASCADE,
        month INT NOT NULL,
        year INT NOT NULL,
        working_days INT,
        present_days INT,
        total_hours NUMERIC(10,2),
        
        -- Salary Components
        gross_salary NUMERIC(10,2),
        net_salary NUMERIC(10,2),
        overtime_hours NUMERIC(10,2),
        overtime_pay NUMERIC(10,2),
        lop_days NUMERIC(5,2),
        lop_deduction NUMERIC(10,2),
        night_shift_allowance NUMERIC(10,2),
        is_finalized BOOLEAN DEFAULT FALSE,
        generated_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(employee_id, month, year)
    );
    """)

    # ============================================================
    # PAYROLL POLICIES
    # ============================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payroll_policies (
        id SERIAL PRIMARY KEY,
        late_grace_minutes INT DEFAULT 0,
        early_exit_grace_minutes INT DEFAULT 0,
        overtime_enabled BOOLEAN DEFAULT TRUE,
        overtime_multiplier NUMERIC(3,2) DEFAULT 1.5,
        holiday_double_pay BOOLEAN DEFAULT TRUE,
        night_shift_allowance NUMERIC(10,2) DEFAULT 0,
        active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    # ============================================================
    # LEAVE TYPES
    # ============================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS leave_types (
        leave_type_id SERIAL PRIMARY KEY,
        name VARCHAR(50) NOT NULL,
        code VARCHAR(10) UNIQUE NOT NULL,
        yearly_quota INT DEFAULT 0,
        is_paid BOOLEAN DEFAULT TRUE,
        carry_forward BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    # ============================================================
    # EMPLOYEE LEAVE BALANCE
    # ============================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employee_leave_balance (
        id SERIAL PRIMARY KEY,
        employee_id INT REFERENCES employees(employee_id) ON DELETE CASCADE,
        leave_type_id INT REFERENCES leave_types(leave_type_id),
        year INT NOT NULL,
        total_quota INT NOT NULL,
        used INT DEFAULT 0,
        remaining INT NOT NULL,
        carry_forwarded INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(employee_id, leave_type_id, year)
    );
    """)

    # ============================================================
    # LEAVE REQUESTS
    # ============================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS leave_requests (
        leave_id SERIAL PRIMARY KEY,
        employee_id INT REFERENCES employees(employee_id) ON DELETE CASCADE,
        leave_type_id INT REFERENCES leave_types(leave_type_id),
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

    # ============================================================
    # LEAVE HISTORY (IMMUTABLE)
    # ============================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS leave_history (
        id SERIAL PRIMARY KEY,
        employee_id INT REFERENCES employees(employee_id),
        leave_type_id INT REFERENCES leave_types(leave_type_id),
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        total_days DECIMAL(5,2) NOT NULL,
        recorded_on TIMESTAMP DEFAULT NOW()
    );
    """)

    # ============================================================
    # WORKFLOWS
    # ============================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS workflows (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        module VARCHAR(50) NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    # ============================================================
    # WORKFLOW STEPS
    # ============================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS workflow_steps (
        id SERIAL PRIMARY KEY,
        workflow_id INT REFERENCES workflows(id) ON DELETE CASCADE,
        step_order INT NOT NULL,
        role VARCHAR(50) NOT NULL,
        is_final BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(workflow_id, step_order)
    );
    """)

    # ============================================================
    # APPROVAL LOGS
    # ============================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS approval_logs (
        id SERIAL PRIMARY KEY,
        module VARCHAR(50) NOT NULL,
        request_id INT NOT NULL,
        workflow_id INT REFERENCES workflows(id),
        step_order INT NOT NULL,
        approver_id INT NOT NULL,
        status VARCHAR(20),
        acted_at TIMESTAMP,
        remarks TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(module, request_id, step_order)
    );
    """)

    # ============================================================
    # REQUEST STATUS
    # ============================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS request_status (
        id SERIAL PRIMARY KEY,
        module VARCHAR(50) NOT NULL,
        request_id INT NOT NULL,
        status VARCHAR(20),
        updated_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(module, request_id)
    );
    """)

    conn.commit()
    cur.close()
    conn.close()

    print("✅ ALL HRMS TABLES CREATED SUCCESSFULLY")

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    create_tables()
