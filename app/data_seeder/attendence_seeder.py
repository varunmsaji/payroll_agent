from datetime import datetime, timedelta, time, date
from app.database.connection import get_connection

EMPLOYEE_ID = 35
SHIFT_ID = 1

BASE_DATE = date(2025, 11, 1)

def seed_event(employee_id, dt, event_type):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO attendance_events (employee_id, event_type, event_time, source)
        VALUES (%s, %s, %s, 'mock');
    """, (employee_id, event_type, dt))

    conn.commit()
    cur.close()
    conn.close()


# ================================
# MOCK DAY GENERATORS
# ================================

def normal_day(day_offset):
    d = BASE_DATE + timedelta(days=day_offset)
    seed_event(EMPLOYEE_ID, datetime.combine(d, time(9, 0)), "check_in")
    seed_event(EMPLOYEE_ID, datetime.combine(d, time(18, 0)), "check_out")

def late_day(day_offset):
    d = BASE_DATE + timedelta(days=day_offset)
    seed_event(EMPLOYEE_ID, datetime.combine(d, time(10, 0)), "check_in")  # 1 hr late
    seed_event(EMPLOYEE_ID, datetime.combine(d, time(18, 0)), "check_out")

def early_exit(day_offset):
    d = BASE_DATE + timedelta(days=day_offset)
    seed_event(EMPLOYEE_ID, datetime.combine(d, time(9, 0)), "check_in")
    seed_event(EMPLOYEE_ID, datetime.combine(d, time(15, 0)), "check_out")  # early exit

def overtime_day(day_offset):
    d = BASE_DATE + timedelta(days=day_offset)
    seed_event(EMPLOYEE_ID, datetime.combine(d, time(9, 0)), "check_in")
    seed_event(EMPLOYEE_ID, datetime.combine(d, time(22, 0)), "check_out")  # overtime

def night_shift_day(day_offset):
    d = BASE_DATE + timedelta(days=day_offset)
    seed_event(EMPLOYEE_ID, datetime.combine(d, time(22, 0)), "check_in")
    seed_event(EMPLOYEE_ID, datetime.combine(d + timedelta(days=1), time(6, 0)), "check_out")

def break_day(day_offset):
    d = BASE_DATE + timedelta(days=day_offset)
    seed_event(EMPLOYEE_ID, datetime.combine(d, time(9, 0)), "check_in")
    seed_event(EMPLOYEE_ID, datetime.combine(d, time(13, 0)), "break_start")
    seed_event(EMPLOYEE_ID, datetime.combine(d, time(13, 30)), "break_end")
    seed_event(EMPLOYEE_ID, datetime.combine(d, time(18, 0)), "check_out")

def half_day(day_offset):
    d = BASE_DATE + timedelta(days=day_offset)
    seed_event(EMPLOYEE_ID, datetime.combine(d, time(9, 0)), "check_in")
    seed_event(EMPLOYEE_ID, datetime.combine(d, time(12, 30)), "check_out")

def absent_day(day_offset):
    pass  # no entry at all → absent

def holiday_work(day_offset):
    d = BASE_DATE + timedelta(days=day_offset)
    seed_event(EMPLOYEE_ID, datetime.combine(d, time(9, 30)), "check_in")
    seed_event(EMPLOYEE_ID, datetime.combine(d, time(17, 30)), "check_out")


# ================================
# RUN SEED
# ================================

if __name__ == "__main__":

    print("🚀 Seeding Mock Attendance Data for Payroll Testing")

    normal_day(0)        # Nov 1
    late_day(1)          # Nov 2
    early_exit(2)        # Nov 3
    overtime_day(3)     # Nov 4
    night_shift_day(4)  # Nov 5
    holiday_work(5)     # Nov 6
    absent_day(6)       # Nov 7
    half_day(7)         # Nov 8
    break_day(8)        # Nov 9
    normal_day(9)       # Nov 10

    print("✅ Attendance Mock Data Seeded Successfully")
