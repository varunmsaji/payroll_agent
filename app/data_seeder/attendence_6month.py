"""
6-MONTH REALISTIC ATTENDANCE SEEDER

- Generates mock attendance for ALL employees in the `employees` table
- Period: last 6 months (DAYS_BACK = 180)
- Uses AttendanceService.recalculate_for_date() so `attendance` is consistent
- Marks events with source = 'mock_6m' for easy cleanup

⚠ Run ONLY on dev / test DB, not production.
"""

from datetime import datetime, timedelta, time, date
import random

from app.database.connection import get_connection
from app.services.attendence_services import AttendanceService

# ================================
# CONFIG
# ================================

DAYS_BACK = 180          # ~6 months
MOCK_SOURCE = "mock_6m"  # used in attendance_events.source

random.seed(42)          # reproducible randomness


# ================================
# HELPERS
# ================================

def get_date_range():
    """
    Returns (start_date, end_date) for the last DAYS_BACK days
    ending yesterday (so today is not included).
    """
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=DAYS_BACK - 1)
    return start_date, end_date


def get_all_employee_ids():
    """
    Fetches all employee IDs from employees table.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT employee_id FROM employees;")
    ids = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return ids


def cleanup_mock_events(start_date: date, end_date: date):
    """
    Clears only previous MOCK events for this date range, if any.
    Attendance rows will be updated by recalc.
    """
    conn = get_connection()
    cur = conn.cursor()

    print(f"🧹 Cleaning old mock events ({MOCK_SOURCE}) from {start_date} to {end_date} ...")

    cur.execute(
        """
        DELETE FROM attendance_events
        WHERE source = %s
          AND event_time::date BETWEEN %s AND %s;
        """,
        (MOCK_SOURCE, start_date, end_date),
    )

    conn.commit()
    cur.close()
    conn.close()


def seed_event(employee_id: int, ts: datetime, event_type: str):
    """
    Inserts a single raw attendance_event row.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO attendance_events (employee_id, event_type, event_time, source)
        VALUES (%s, %s, %s, %s);
        """,
        (employee_id, event_type, ts, MOCK_SOURCE),
    )

    conn.commit()
    cur.close()
    conn.close()


def recalc(employee_id: int, d: date):
    """
    Unlocks (if needed) and recalculates attendance for a single day.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Force unlock before recalculation (safe for dev/mock)
    cur.execute(
        """
        UPDATE attendance
        SET is_payroll_locked = FALSE,
            locked_at = NULL
        WHERE employee_id = %s AND date = %s;
        """,
        (employee_id, d),
    )

    conn.commit()
    cur.close()
    conn.close()

    # Let your core logic do the real calculation
    AttendanceService.recalculate_for_date(employee_id, d)


# ================================
# DAY PATTERN GENERATORS
# ================================

def normal_day(e: int, d: date):
    # Slight random shift around 9:00–9:15 and 18:00–18:15
    in_min = random.randint(0, 15)
    out_min = random.randint(0, 15)
    seed_event(e, datetime.combine(d, time(9, in_min)), "check_in")
    seed_event(e, datetime.combine(d, time(18, out_min)), "check_out")


def late_day(e: int, d: date):
    # Late by 30–90 minutes
    late_min = random.randint(30, 90)
    checkin = (datetime.combine(d, time(9, 0)) + timedelta(minutes=late_min))
    seed_event(e, checkin, "check_in")
    seed_event(e, datetime.combine(d, time(18, 0)), "check_out")


def early_exit_day(e: int, d: date):
    # Leave 1–3 hours early
    seed_event(e, datetime.combine(d, time(9, 0)), "check_in")
    early_min = random.randint(60, 180)
    checkout = (datetime.combine(d, time(18, 0)) - timedelta(minutes=early_min))
    seed_event(e, checkout, "check_out")


def overtime_day(e: int, d: date):
    # Work 2–4 extra hours
    seed_event(e, datetime.combine(d, time(9, 0)), "check_in")
    extra_min = random.randint(120, 240)
    checkout = (datetime.combine(d, time(18, 0)) + timedelta(minutes=extra_min))
    seed_event(e, checkout, "check_out")


def break_day(e: int, d: date):
    # Normal day with 1 hour lunch break
    seed_event(e, datetime.combine(d, time(9, 0)), "check_in")
    seed_event(e, datetime.combine(d, time(13, 0)), "break_start")
    seed_event(e, datetime.combine(d, time(14, 0)), "break_end")
    seed_event(e, datetime.combine(d, time(18, 0)), "check_out")


def half_day(e: int, d: date):
    # Work only morning
    seed_event(e, datetime.combine(d, time(9, 0)), "check_in")
    seed_event(e, datetime.combine(d, time(13, 0)), "check_out")


def night_shift_day(e: int, d: date):
    # Night shift from 10PM to 6AM next day
    seed_event(e, datetime.combine(d, time(22, 0)), "check_in")
    seed_event(e, datetime.combine(d + timedelta(days=1), time(6, 0)), "check_out")


def absent_day(e: int, d: date):
    # No events at all -> will be marked ABSENT by logic
    pass


def weekend_work_day(e: int, d: date):
    # Weekend but worked slightly shorter / normal
    seed_event(e, datetime.combine(d, time(10, 0)), "check_in")
    seed_event(e, datetime.combine(d, time(16, 0)), "check_out")


# ================================
# MAIN DAY PATTERN DECISION
# ================================

def generate_day_for_employee(employee_id: int, d: date):
    """
    Decide what kind of day this should be for a given employee and date,
    then seed matching events.
    """

    weekday = d.weekday()  # 0=Mon, 6=Sun

    # ---------- WEEKENDS ----------
    if weekday >= 5:
        # 80%: pure week off (no events)
        # 20%: worked (maybe overtime or shorter shift)
        r = random.random()
        if r < 0.8:
            # weekend off
            absent_day(employee_id, d)  # no events; logic will mark week_off, not absent
        else:
            # weekend work
            weekend_work_day(employee_id, d)
        return

    # ---------- WEEKDAYS ----------
    r = random.random()

    if r < 0.60:
        # 60% normal days
        normal_day(employee_id, d)
    elif r < 0.70:
        # 10% late days
        late_day(employee_id, d)
    elif r < 0.78:
        # 8% early exit days
        early_exit_day(employee_id, d)
    elif r < 0.86:
        # 8% half days
        half_day(employee_id, d)
    elif r < 0.94:
        # 8% with explicit long break
        break_day(employee_id, d)
    else:
        # 6% completely absent
        absent_day(employee_id, d)


# ================================
# SEEDING LOOP
# ================================

def seed_employee_over_range(employee_id: int, start_date: date, end_date: date):
    """
    Seeds 6-month realistic attendance for one employee.
    """
    print(f"\n👤 Seeding attendance for Employee: {employee_id}")

    current = start_date
    while current <= end_date:
        generate_day_for_employee(employee_id, current)
        recalc(employee_id, current)
        current += timedelta(days=1)


# ================================
# ENTRY POINT
# ================================

if __name__ == "__main__":

    start_date, end_date = get_date_range()

    print("\n🚀 6-MONTH ATTENDANCE SEEDER (MOCK)")
    print(f"   Period: {start_date} → {end_date}")
    print(f"   Source tag in attendance_events: '{MOCK_SOURCE}'")
    print("   ⚠ Use only on development / staging databases.\n")

    employees = get_all_employee_ids()

    if not employees:
        print("❌ No employees found in `employees` table. Aborting.")
        exit(1)

    # Optional cleanup of only old mock events for this range
    cleanup_mock_events(start_date, end_date)

    for emp_id in employees:
        seed_employee_over_range(emp_id, start_date, end_date)

    print("\n✅✅✅ DONE: 6-MONTH MOCK ATTENDANCE GENERATED FOR ALL EMPLOYEES ✅✅✅\n")
