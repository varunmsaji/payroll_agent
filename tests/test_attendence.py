import requests
import json
import time

BASE_URL = "http://localhost:8000"
EMPLOYEE_ID = 36
DATE = "2026-01-11"   # make sure shift exists for this date


def call(action_time, label):
    print("\n" + "=" * 60)
    print(label)
    print("TIME:", action_time)

    response = requests.post(
        f"{BASE_URL}/attendance/manual",
        data={
            "employee_id": EMPLOYEE_ID,
            "action_time": action_time,
        },
        timeout=10,
    )

    print("STATUS:", response.status_code)
    try:
        print(json.dumps(response.json(), indent=2))
    except Exception:
        print(response.text)

    time.sleep(0.3)


# =====================================================
# TEST SEQUENCE
# =====================================================
print("⚠️ Make sure DB is clean for employee 36")
print("""
DELETE FROM attendance_events WHERE employee_id = 36;
DELETE FROM attendance WHERE employee_id = 36;
""")
input("Run the SQL above and press ENTER to continue...")


# 1️⃣ CHECK IN
call(f"{DATE}T09:00:00", "CHECK-IN")

# 2️⃣ BREAK START
call(f"{DATE}T13:00:00", "BREAK START")

# 3️⃣ BREAK END
call(f"{DATE}T14:00:00", "BREAK END")

# 4️⃣ CHECK OUT
call(f"{DATE}T18:00:00", "CHECK-OUT")


print("\n✅ TEST COMPLETED")
print("""
Check final attendance row:

SELECT
    date,
    check_in,
    check_out,
    net_hours,
    break_minutes,
    late_minutes,
    early_exit_minutes,
    overtime_minutes,
    status
FROM attendance
WHERE employee_id = 36;
""")
