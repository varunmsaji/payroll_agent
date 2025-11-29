import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================
# DATABASE CONFIG (YOUR PARAMS)
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

    # --------------------------
    # EMPLOYEES
    # --------------------------
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
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    # --------------------------
    # SHIFTS
    # --------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS shifts (
        shift_id SERIAL PRIMARY KEY,
        shift_name VARCHAR(100) NOT NULL,
        start_time TIME NOT NULL,
        end_time TIME NOT NULL,
        is_night_shift BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    # --------------------------
    # EMPLOYEE SHIFT ASSIGNMENT
    # --------------------------
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

    # --------------------------
    # HOLIDAYS (NEW)
    # --------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS holidays (
        id SERIAL PRIMARY KEY,
        holiday_date DATE UNIQUE NOT NULL,
        name VARCHAR(100) NOT NULL,
        is_optional BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    # --------------------------
    # RAW ATTENDANCE EVENTS
    # --------------------------
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

    # --------------------------
    # PROCESSED DAILY ATTENDANCE (UPDATED)
    # --------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        attendance_id SERIAL PRIMARY KEY,
        employee_id INT REFERENCES employees(employee_id) ON DELETE CASCADE,
        shift_id INT REFERENCES shifts(shift_id) ON DELETE SET NULL,
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

    # --------------------------
    # SALARY STRUCTURE
    # --------------------------
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

    # --------------------------
    # PAYROLL (UPDATED)
    # --------------------------
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
        basic_pay NUMERIC(10,2),
        hra_pay NUMERIC(10,2),
        allowances_pay NUMERIC(10,2),
        
        -- Overtime & Penalties
        overtime_hours NUMERIC(5,2) DEFAULT 0,
        overtime_pay NUMERIC(10,2) DEFAULT 0,
        late_penalty NUMERIC(10,2) DEFAULT 0,
        early_penalty NUMERIC(10,2) DEFAULT 0,
        lop_days NUMERIC(5,2) DEFAULT 0,
        lop_deduction NUMERIC(10,2) DEFAULT 0,
        
        -- Additional
        night_shift_allowance NUMERIC(10,2) DEFAULT 0,
        holiday_pay NUMERIC(10,2) DEFAULT 0,
        
        is_finalized BOOLEAN DEFAULT FALSE,
        generated_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(employee_id, month, year)
    );
    """)

    conn.commit()
    cur.close()
    conn.close()

    print("✅ HRMS tables (including raw attendance) created successfully!")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    create_tables()
