import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import random

# ============================================================
# DB CONFIG
# ============================================================
DB_PARAMS = {
    "dbname": "hrms_db",
    "user": "varun",
    "password": "varun@123",
    "host": "localhost",
    "port": 5432,
}


def get_connection():
    return psycopg2.connect(**DB_PARAMS)


# ============================================================
# 1️⃣ INSERT MOCK EMPLOYEES
# ============================================================
def seed_employees(n=10):
    print(f"➡ Seeding {n} employees...")

    first_names = ["Varun", "Rahul", "Sneha", "Priya", "Karan", "Satish", "Anita", "Ravi", "Divya", "Megha"]
    last_names = ["Singh", "Kumar", "Reddy", "Sharma", "Nair", "Mohan", "Patil", "Gupta", "Shetty", "Joshi"]
    designations = ["Developer", "Designer", "Manager", "HR", "DevOps", "Sales"]
    departments = ["IT", "HR", "Finance", "Sales", "Marketing"]

    conn = get_connection()
    cur = conn.cursor()

    for i in range(n):
        fn = random.choice(first_names)
        ln = random.choice(last_names)

        cur.execute("""
            INSERT INTO employees 
            (first_name, last_name, email, phone, designation, department, date_of_joining, base_salary)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            fn,
            ln,
            f"{fn.lower()}.{ln.lower()}{i}@gmail.com",
            f"98765{random.randint(10000,99999)}",
            random.choice(designations),
            random.choice(departments),
            datetime.now().date() - timedelta(days=random.randint(30, 1000)),
            random.randint(20000, 80000)
        ))

    conn.commit()
    conn.close()
    print("✅ Employees seeded!")


# ============================================================
# 2️⃣ INSERT MOCK SHIFTS
# ============================================================
def seed_shifts():
    print("➡ Seeding shifts...")
    conn = get_connection()
    cur = conn.cursor()

    shifts = [
        ("General Shift", "09:00", "17:00", False),
        ("Morning Shift", "07:00", "15:00", False),
        ("Evening Shift", "14:00", "22:00", False),
        ("Night Shift", "22:00", "06:00", True),
    ]

    for s in shifts:
        cur.execute("""
            INSERT INTO shifts (shift_name, start_time, end_time, is_night_shift)
            VALUES (%s,%s,%s,%s)
        """, s)

    conn.commit()
    conn.close()
    print("✅ Shifts seeded!")


# ============================================================
# 3️⃣ ASSIGN SHIFT TO EMPLOYEES
# ============================================================
def assign_shifts():
    print("➡ Assigning shifts...")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT employee_id FROM employees")
    employees = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT shift_id FROM shifts")
    shifts = [r[0] for r in cur.fetchall()]

    for emp in employees:
        cur.execute("""
            INSERT INTO employee_shifts (employee_id, shift_id, effective_from)
            VALUES (%s,%s,%s)
        """, (
            emp,
            random.choice(shifts),
            datetime.now().date() - timedelta(days=60)
        ))

    conn.commit()
    conn.close()
    print("✅ Shifts assigned!")


# ============================================================
# 4️⃣ INSERT RAW ATTENDANCE EVENTS
# ============================================================
def seed_attendance_events(days=7):
    print(f"➡ Seeding attendance events for last {days} days...")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT employee_id FROM employees")
    employees = [r[0] for r in cur.fetchall()]

    for day in range(days):
        date_of_day = datetime.now().date() - timedelta(days=day)

        for emp in employees:
            # Generate check-in between 8:40 AM to 9:40 AM
            check_in_time = datetime.combine(date_of_day, datetime.strptime("09:00", "%H:%M").time()) \
                            + timedelta(minutes=random.randint(-20, 40))

            # check-out after 8–10 hours
            check_out_time = check_in_time + timedelta(hours=random.uniform(8, 10))

            # ADD check-in
            cur.execute("""
                INSERT INTO attendance_events (employee_id, event_type, event_time)
                VALUES (%s, %s, %s)
            """, (emp, "check_in", check_in_time))

            # ADD check-out
            cur.execute("""
                INSERT INTO attendance_events (employee_id, event_type, event_time)
                VALUES (%s, %s, %s)
            """, (emp, "check_out", check_out_time))

    conn.commit()
    conn.close()
    print("✅ Attendance events seeded!")


# ============================================================
# 5️⃣ PROCESS DAILY ATTENDANCE FROM RAW EVENTS
# ============================================================
def process_attendance_for_all(days=7):
    print("➡ Processing attendance...")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT employee_id FROM employees")
    employees = [r[0] for r in cur.fetchall()]

    for day in range(days):
        date_of_day = datetime.now().date() - timedelta(days=day)

        for emp in employees:
            cur.execute("""
                SELECT event_type, event_time 
                FROM attendance_events
                WHERE employee_id=%s AND DATE(event_time)=%s
                ORDER BY event_time ASC
            """, (emp, date_of_day))

            events = cur.fetchall()
            if not events:
                continue

            check_in = next((e[1] for e in events if e[0] == "check_in"), None)
            check_out = next((e[1] for e in events if e[0] == "check_out"), None)

            if check_in and check_out:
                total_hours = (check_out - check_in).seconds / 3600
            else:
                total_hours = None

            cur.execute("""
                INSERT INTO attendance (employee_id, date, check_in, check_out, total_hours)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (employee_id, date)
                DO UPDATE SET check_in=EXCLUDED.check_in, check_out=EXCLUDED.check_out, total_hours=EXCLUDED.total_hours
            """, (emp, date_of_day, check_in, check_out, total_hours))

    conn.commit()
    conn.close()
    print("✅ Daily attendance processed!")


# ============================================================
# 6️⃣ SEED SALARY STRUCTURE
# ============================================================
def seed_salary_structure():
    print("➡ Seeding salary structure...")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT employee_id FROM employees")
    employees = [r[0] for r in cur.fetchall()]

    for emp in employees:
        basic = random.randint(15000, 50000)
        hra = basic * 0.4
        allowances = random.randint(2000, 10000)
        deductions = random.randint(500, 2000)

        cur.execute("""
            INSERT INTO salary_structure 
            (employee_id, basic, hra, allowances, deductions, effective_from)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            emp, basic, hra, allowances, deductions,
            datetime.now().date() - timedelta(days=30)
        ))

    conn.commit()
    conn.close()
    print("✅ Salary structure seeded!")


# ============================================================
# 7️⃣ GENERATE PAYROLL
# ============================================================
def generate_payroll(month, year):
    print(f"➡ Generating payroll for {month}/{year}...")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT employee_id FROM employees")
    employees = [r[0] for r in cur.fetchall()]

    for emp in employees:
        cur.execute("""
            SELECT SUM(total_hours) FROM attendance
            WHERE employee_id=%s AND EXTRACT(MONTH FROM date)=%s AND EXTRACT(YEAR FROM date)=%s
        """, (emp, month, year))

        total_hours = cur.fetchone()[0] or 0
        present_days = total_hours // 8

        cur.execute("""
            SELECT basic, hra, allowances, deductions
            FROM salary_structure WHERE employee_id=%s 
            ORDER BY effective_from DESC LIMIT 1
        """, (emp,))

        basic, hra, allow, deduct = cur.fetchone()
        gross = basic + hra + allow
        net = gross - deduct

        cur.execute("""
            INSERT INTO payroll 
            (employee_id, month, year, working_days, present_days, total_hours, gross_salary, net_salary)
            VALUES (%s,%s,%s,26,%s,%s,%s,%s)
        """, (
            emp, month, year, present_days, total_hours, gross, net
        ))

    conn.commit()
    conn.close()
    print("✅ Payroll generated!")



# ============================================================
# 8️⃣ SEED LEAVE TYPES
# ============================================================
def seed_leave_types():
    print("➡ Seeding leave types...")

    leave_types = [
        ("Paid Leave", "PL", 12, True, True),
        ("Sick Leave", "SL", 6, True, False),
        ("Unpaid Leave", "UL", 0, False, False)
    ]

    conn = get_connection()
    cur = conn.cursor()

    for lt in leave_types:
        cur.execute("""
            INSERT INTO leave_types (name, code, yearly_quota, is_paid, carry_forward)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (code) DO NOTHING
        """, lt)

    conn.commit()
    conn.close()
    print("✅ Leave types seeded!")



# ============================================================
# 9️⃣ SEED LEAVE BALANCES
# ============================================================
def seed_leave_balances(year=None):
    print("➡ Seeding leave balances...")

    if year is None:
        year = datetime.now().year

    conn = get_connection()
    cur = conn.cursor()

    # Get all employees
    cur.execute("SELECT employee_id FROM employees")
    employees = [r[0] for r in cur.fetchall()]

    # Get all leave types
    cur.execute("SELECT leave_type_id, yearly_quota FROM leave_types")
    leave_types = cur.fetchall()

    for emp in employees:
        for lt in leave_types:
            leave_type_id, quota = lt
            cur.execute("""
                INSERT INTO employee_leave_balance 
                (employee_id, leave_type_id, year, total_quota, used, remaining)
                VALUES (%s,%s,%s,%s,0,%s)
                ON CONFLICT (employee_id, leave_type_id, year) DO NOTHING
            """, (
                emp, leave_type_id, year, quota, quota
            ))

    conn.commit()
    conn.close()
    print("✅ Leave balances seeded!")



# ============================================================
# 🔟 SEED LEAVE REQUESTS + HISTORY
# ============================================================
def seed_leave_requests(months=3):
    print("➡ Seeding leave requests...")

    conn = get_connection()
    cur = conn.cursor()

    # Fetch employees
    cur.execute("SELECT employee_id FROM employees")
    employees = [r[0] for r in cur.fetchall()]

    # Fetch leave types
    cur.execute("SELECT leave_type_id FROM leave_types")
    leave_types = [r[0] for r in cur.fetchall()]

    for emp in employees:
        for _ in range(random.randint(1, 4)):  # 1 to 4 leave requests
            leave_type = random.choice(leave_types)

            # Random last X months
            start = datetime.now().date() - timedelta(days=random.randint(1, months * 30))
            duration = random.choice([1, 1.5, 2, 3])
            end = start + timedelta(days=int(duration))

            # Insert leave request
            cur.execute("""
                INSERT INTO leave_requests 
                (employee_id, leave_type_id, start_date, end_date, total_days, reason, status, approved_by, approved_on)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                emp, leave_type, start, end,
                duration, "Personal reason",
                "approved", random.choice(employees),
                datetime.now()
            ))

            # Update leave balance (reduce usage)
            cur.execute("""
                UPDATE employee_leave_balance
                SET used = used + %s,
                    remaining = remaining - %s
                WHERE employee_id=%s AND leave_type_id=%s AND year=%s
            """, (
                duration, duration, emp, leave_type, datetime.now().year
            ))

            # Insert into leave history
            cur.execute("""
                INSERT INTO leave_history
                (employee_id, leave_type_id, start_date, end_date, total_days)
                VALUES (%s,%s,%s,%s,%s)
            """, (
                emp, leave_type, start, end, duration
            ))

    conn.commit()
    conn.close()
    print("✅ Leave requests + history seeded!")




# ============================================================
# 1️⃣ SEED LEAVE TYPES
# ============================================================
def seed_leave_types():
    print("➡ Seeding leave types...")

    leave_types = [
        ("Paid Leave", "PL", 12, True, True),
        ("Sick Leave", "SL", 6, True, False),
        ("Unpaid Leave", "UL", 0, False, False)
    ]

    conn = get_connection()
    cur = conn.cursor()

    for lt in leave_types:
        cur.execute("""
            INSERT INTO leave_types (name, code, yearly_quota, is_paid, carry_forward)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (code) DO NOTHING
        """, lt)

    conn.commit()
    conn.close()
    print("✅ Leave types seeded!")


# ============================================================
# 2️⃣ SEED LEAVE BALANCES FOR ALL EMPLOYEES
# ============================================================
def seed_leave_balances(year=None):
    print("➡ Seeding leave balances...")

    if year is None:
        year = datetime.now().year

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT employee_id FROM employees")
    employees = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT leave_type_id, yearly_quota FROM leave_types")
    leave_types = cur.fetchall()

    for emp in employees:
        for lt in leave_types:
            leave_type_id, quota = lt
            cur.execute("""
                INSERT INTO employee_leave_balance 
                (employee_id, leave_type_id, year, total_quota, used, remaining)
                VALUES (%s,%s,%s,%s,0,%s)
                ON CONFLICT (employee_id, leave_type_id, year) DO NOTHING
            """, (emp, leave_type_id, year, quota, quota))

    conn.commit()
    conn.close()
    print("✅ Leave balances seeded!")


# ============================================================
# 3️⃣ SEED LEAVE REQUESTS (APPROVED + PENDING)
# ============================================================
def seed_leave_requests(months_back=3):
    print("➡ Seeding leave requests, balances & history...")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT employee_id FROM employees")
    employees = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT leave_type_id, is_paid FROM leave_types")
    leave_types = cur.fetchall()

    current_year = datetime.now().year

    for emp in employees:
        for _ in range(random.randint(2, 5)):  # 2–5 leaves per employee
            leave_type_id, is_paid = random.choice(leave_types)

            start = datetime.now().date() - timedelta(days=random.randint(1, months_back * 30))
            duration = random.choice([1, 2, 3])
            end = start + timedelta(days=duration)

            status = random.choice(["approved", "pending"])

            # 👉 Insert leave request
            cur.execute("""
                INSERT INTO leave_requests 
                (employee_id, leave_type_id, start_date, end_date, total_days, reason, status, approved_by, approved_on)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING leave_id
            """, (
                emp,
                leave_type_id,
                start,
                end,
                duration,
                "Auto seeded leave",
                status,
                random.choice(employees) if status == "approved" else None,
                datetime.now() if status == "approved" else None
            ))

            # 👉 IF APPROVED → Update balance + insert history
            if status == "approved" and is_paid:
                cur.execute("""
                    UPDATE employee_leave_balance
                    SET used = used + %s,
                        remaining = remaining - %s
                    WHERE employee_id=%s AND leave_type_id=%s AND year=%s
                """, (duration, duration, emp, leave_type_id, current_year))

                cur.execute("""
                    INSERT INTO leave_history
                    (employee_id, leave_type_id, start_date, end_date, total_days)
                    VALUES (%s,%s,%s,%s,%s)
                """, (emp, leave_type_id, start, end, duration))

    conn.commit()
    conn.close()
    print("✅ Leave requests + history + balances updated!")


# ============================================================
# RUN EVERYTHING
# ============================================================
if __name__ == "__main__":
    # seed_employees()
    # seed_shifts()
    # assign_shifts()
    # seed_attendance_events()
    # process_attendance_for_all()
    # seed_salary_structure()
    # generate_payroll(month=datetime.now().month, year=datetime.now().year)
    seed_leave_types()
    seed_leave_balances()
    seed_leave_requests()
    print("\n🎉 MOCK DATA SEEDING COMPLETE!\n")
