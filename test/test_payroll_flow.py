import requests
import json
from datetime import date, timedelta

BASE_URL = "http://localhost:8000"

def test_payroll_flow():
    print("🚀 Starting Payroll Flow Verification...")

    # 1. Create a Test Employee
    print("\n1️⃣ Creating Test Employee...")
    emp_data = {
        "first_name": "Payroll",
        "last_name": "Tester",
        "email": "payroll.tester@example.com",
        "phone": "9999999999",
        "designation": "Tester",
        "department": "QA",
        "date_of_joining": "2025-01-01",
        "base_salary": 50000
    }
    # Assuming there's an endpoint to create employee, or we use DB directly.
    # Let's try to use the API if available, otherwise we might need to insert directly.
    # Checking previous context, there is `employee_detail.py`.
    # Let's assume we can create via `POST /employees` (standard convention) or similar.
    # If not, I'll use a direct DB insert helper here for reliability in test.
    
    # Actually, let's use direct DB for setup to avoid API dependency issues for setup.
    from app.database.connection import get_connection
    from psycopg2.extras import RealDictCursor
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Clean up previous test
    cur.execute("DELETE FROM employees WHERE email = %s", (emp_data["email"],))
    
    cur.execute("""
        INSERT INTO employees (first_name, last_name, email, phone, designation, department, date_of_joining, base_salary)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING employee_id;
    """, (emp_data["first_name"], emp_data["last_name"], emp_data["email"], emp_data["phone"], 
          emp_data["designation"], emp_data["department"], emp_data["date_of_joining"], emp_data["base_salary"]))
    employee_id = cur.fetchone()["employee_id"]
    conn.commit()
    print(f"✅ Employee Created: ID {employee_id}")

    # 2. Add Salary Structure
    print("\n2️⃣ Adding Salary Structure...")
    # Basic: 30000, HRA: 10000, Allowances: 10000, Deductions: 2000
    cur.execute("""
        INSERT INTO salary_structure (employee_id, basic, hra, allowances, deductions, effective_from)
        VALUES (%s, 30000, 10000, 10000, 2000, '2025-01-01');
    """, (employee_id,))
    conn.commit()
    print("✅ Salary Structure Added")

    # 3. Add Attendance Data (Simulate a month)
    # Month: November 2025 (30 days)
    # Scenario:
    # - 20 days present
    # - 2 days late (30 mins each) -> Total 60 mins late
    # - 1 day overtime (2 hours) -> Total 120 mins overtime
    # - 1 day night shift
    # - 1 day holiday worked
    
    print("\n3️⃣ Seeding Attendance Data...")
    month = 11
    year = 2025
    
    # Clear existing attendance
    cur.execute("DELETE FROM attendance WHERE employee_id=%s AND EXTRACT(MONTH FROM date)=%s", (employee_id, month))
    
    # Day 1: Normal Present
    cur.execute("""
        INSERT INTO attendance (employee_id, date, net_hours, status, is_payroll_locked)
        VALUES (%s, '2025-11-01', 8, 'present', FALSE);
    """, (employee_id,))
    
    # Day 2: Late (30 mins)
    cur.execute("""
        INSERT INTO attendance (employee_id, date, net_hours, late_minutes, is_late, status, is_payroll_locked)
        VALUES (%s, '2025-11-02', 7.5, 30, TRUE, 'present', FALSE);
    """, (employee_id,))

    # Day 3: Late (30 mins)
    cur.execute("""
        INSERT INTO attendance (employee_id, date, net_hours, late_minutes, is_late, status, is_payroll_locked)
        VALUES (%s, '2025-11-03', 7.5, 30, TRUE, 'present', FALSE);
    """, (employee_id,))

    # Day 4: Overtime (2 hours = 120 mins)
    cur.execute("""
        INSERT INTO attendance (employee_id, date, net_hours, overtime_minutes, is_overtime, status, is_payroll_locked)
        VALUES (%s, '2025-11-04', 10, 120, TRUE, 'present', FALSE);
    """, (employee_id,))

    # Day 5: Night Shift
    cur.execute("""
        INSERT INTO attendance (employee_id, date, net_hours, is_night_shift, status, is_payroll_locked)
        VALUES (%s, '2025-11-05', 8, TRUE, 'present', FALSE);
    """, (employee_id,))

    # Day 6: Holiday Worked
    cur.execute("""
        INSERT INTO attendance (employee_id, date, net_hours, is_holiday, status, is_payroll_locked)
        VALUES (%s, '2025-11-06', 8, TRUE, 'present', FALSE);
    """, (employee_id,))
    
    # Fill remaining 14 days as normal present
    for day in range(7, 21):
        cur.execute("""
            INSERT INTO attendance (employee_id, date, net_hours, status, is_payroll_locked)
            VALUES (%s, %s, 8, 'present', FALSE);
        """, (employee_id, f"2025-11-{day:02d}"))

    conn.commit()
    print("✅ Attendance Seeded (20 days present, mixed scenarios)")

    # 4. Generate Payroll via API
    print("\n4️⃣ Generating Payroll via API...")
    payload = {"employee_id": employee_id, "month": month, "year": year}
    response = requests.post(f"{BASE_URL}/payroll/generate", json=payload)
    
    if response.status_code != 200:
        print(f"❌ Failed to generate payroll: {response.text}")
        return

    data = response.json()["data"]
    print("✅ Payroll Generated Successfully")
    print(json.dumps(data, indent=2, default=str))

    # 5. Verify Calculations
    print("\n5️⃣ Verifying Calculations...")
    
    # Constants
    BASIC = 30000
    STANDARD_DAYS = 30
    HOURLY_RATE = (BASIC / STANDARD_DAYS) / 8  # 30000 / 30 / 8 = 125
    MINUTE_RATE = HOURLY_RATE / 60             # 125 / 60 = 2.0833...

    # Expected Values
    exp_overtime_pay = round(120 * MINUTE_RATE * 2.0, 2) # 120 * 2.0833 * 2 = 500.0
    exp_late_penalty = round(60 * MINUTE_RATE, 2)        # 60 * 2.0833 = 125.0
    
    # LOP: Expected 26 days, Present 20 days -> LOP 6 days
    exp_lop_deduction = round(6 * (BASIC / STANDARD_DAYS), 2) # 6 * 1000 = 6000.0
    
    exp_night_shift_allowance = 200 * 1 # 1 night shift
    exp_holiday_pay = round(1 * (BASIC / STANDARD_DAYS), 2) # 1 holiday * 1000 = 1000.0

    print(f"Expected Overtime: {exp_overtime_pay}, Actual: {data['overtime_pay']}")
    print(f"Expected Late Penalty: {exp_late_penalty}, Actual: {data['late_penalty']}")
    print(f"Expected LOP Deduction: {exp_lop_deduction}, Actual: {data['lop_deduction']}")
    print(f"Expected Night Shift: {exp_night_shift_allowance}, Actual: {data['night_shift_allowance']}")
    print(f"Expected Holiday Pay: {exp_holiday_pay}, Actual: {data['holiday_pay']}")

    # 6. Lock Payroll
    print("\n6️⃣ Locking Payroll...")
    lock_payload = {"month": month, "year": year}
    lock_response = requests.post(f"{BASE_URL}/payroll/lock", json=lock_payload)
    
    if lock_response.status_code == 200:
        print("✅ Payroll Locked Successfully")
    else:
        print(f"❌ Failed to lock payroll: {lock_response.text}")

    # 7. Verify Lock in DB
    cur.execute("SELECT is_payroll_locked FROM attendance WHERE employee_id=%s AND date='2025-11-01'", (employee_id,))
    is_locked = cur.fetchone()["is_payroll_locked"]
    if is_locked:
        print("✅ Attendance Record is LOCKED")
    else:
        print("❌ Attendance Record is NOT LOCKED")

    conn.close()

if __name__ == "__main__":
    test_payroll_flow()
