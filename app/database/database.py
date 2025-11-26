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
    # RAW ATTENDANCE EVENTS (Recommended)
    # --------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance_events (
        event_id SERIAL PRIMARY KEY,
        employee_id INT REFERENCES employees(employee_id) ON DELETE CASCADE,
        event_type VARCHAR(20) NOT NULL, 
            -- Allowed: check_in, check_out, break_start, break_end
        event_time TIMESTAMP NOT NULL,
        source VARCHAR(40) DEFAULT 'manual',
        meta JSONB,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    # --------------------------
    # PROCESSED DAILY ATTENDANCE
    # --------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        attendance_id SERIAL PRIMARY KEY,
        employee_id INT REFERENCES employees(employee_id) ON DELETE CASCADE,
        date DATE NOT NULL,
        check_in TIMESTAMP,
        check_out TIMESTAMP,
        total_hours NUMERIC(5,2),
        status VARCHAR(20) DEFAULT 'present',
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
    # PAYROLL
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
        gross_salary NUMERIC(10,2),
        net_salary NUMERIC(10,2),
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
