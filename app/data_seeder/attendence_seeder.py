from datetime import datetime, timedelta, time, date
from app.database.connection import get_connection
from app.services.attendence_services import AttendanceService

BASE_DATE = date(2025, 11, 1)

print("⚠️  MOCK SEEDER: This WILL generate attendance for ALL employees")

# ================================
# FETCH ALL EMPLOYEES
# ================================

def get_all_employee_ids():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT employee_id FROM employees;")
    ids = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return ids


# ================================
# RAW EVENT SEEDER
# ================================

def seed_event(employee_id, ts, event_type):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO attendance_events (employee_id, event_type, event_time, source)
        VALUES (%s, %s, %s, 'mock');
    """, (employee_id, event_type, ts))

    conn.commit()
    cur.close()
    conn.close()


# ================================
# DAY TYPE GENERATORS
# ================================

def normal_day(e, d):
    seed_event(e, datetime.combine(d, time(9, 0)), "check_in")
    seed_event(e, datetime.combine(d, time(18, 0)), "check_out")

def late_day(e, d):
    seed_event(e, datetime.combine(d, time(10, 0)), "check_in")
    seed_event(e, datetime.combine(d, time(18, 0)), "check_out")

def early_exit(e, d):
    seed_event(e, datetime.combine(d, time(9, 0)), "check_in")
    seed_event(e, datetime.combine(d, time(15, 0)), "check_out")

def overtime_day(e, d):
    seed_event(e, datetime.combine(d, time(9, 0)), "check_in")
    seed_event(e, datetime.combine(d, time(22, 0)), "check_out")

def night_shift_day(e, d):
    seed_event(e, datetime.combine(d, time(22, 0)), "check_in")
    seed_event(e, datetime.combine(d + timedelta(days=1), time(6, 0)), "check_out")

def break_day(e, d):
    seed_event(e, datetime.combine(d, time(9, 0)), "check_in")
    seed_event(e, datetime.combine(d, time(13, 0)), "break_start")
    seed_event(e, datetime.combine(d, time(13, 30)), "break_end")
    seed_event(e, datetime.combine(d, time(18, 0)), "check_out")

def half_day(e, d):
    seed_event(e, datetime.combine(d, time(9, 0)), "check_in")
    seed_event(e, datetime.combine(d, time(12, 30)), "check_out")

def absent_day(e, d):
    pass

def holiday_work(e, d):
    seed_event(e, datetime.combine(d, time(9, 30)), "check_in")
    seed_event(e, datetime.combine(d, time(17, 30)), "check_out")


# ================================
# FORCE SAFE RECALC (UNLOCK FIRST)
# ================================

def recalc(employee_id, d):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE attendance
        SET is_payroll_locked = FALSE,
            locked_at = NULL
        WHERE employee_id = %s AND date = %s;
    """, (employee_id, d))

    conn.commit()
    cur.close()
    conn.close()

    AttendanceService.recalculate_for_date(employee_id, d)


# ================================
# SEED ONE EMPLOYEE
# ================================

def seed_employee(employee_id):

    print(f"\n👤 Seeding Employee: {employee_id}")

    schedule = [
        normal_day,
        late_day,
        early_exit,
        overtime_day,
        night_shift_day,
        holiday_work,
        absent_day,
        half_day,
        break_day,
        normal_day
    ]

    for i, func in enumerate(schedule):
        d = BASE_DATE + timedelta(days=i)
        func(employee_id, d)
        recalc(employee_id, d)
        print(f"  ✅ {d} -> {func.__name__}")


# ================================
# RUN FOR ALL EMPLOYEES
# ================================

if __name__ == "__main__":

    print("\n🚀 SEEDING MOCK ATTENDANCE FOR ALL EMPLOYEES\n")

    employees = get_all_employee_ids()

    if not employees:
        print("❌ No employees found in DB")
        exit()

    for emp in employees:
        seed_employee(emp)

    print("\n✅✅✅ ALL EMPLOYEES SEEDED SUCCESSFULLY ✅✅✅\n")
