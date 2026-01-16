"""
Python client to test Attendance overtime via /attendance/manual API

Employee: 36
Date: 2026-01-11
Scenario:
- 09:00 check-in
- 13:00 break start
- 13:30 break end
- 20:00 check-out (overtime)
"""

import requests

BASE_URL = "http://localhost:8000"  # change if needed
ENDPOINT = f"{BASE_URL}/attendance/manual"

EMPLOYEE_ID = 36


def call_api(action_time):
    response = requests.post(
        ENDPOINT,
        data={
            "employee_id": EMPLOYEE_ID,
            "action_time": action_time,
        },
        timeout=10,
    )

    if response.status_code != 200:
        print("❌ ERROR:", response.status_code, response.text)
        return

    data = response.json()
    print(
        f"✅ {data['action'].upper()} @ {data['used_time']}"
    )


def run_test():
    print("🚀 STARTING ATTENDANCE OVERTIME TEST\n")

    # 1️⃣ CHECK-IN
    call_api("2026-01-11T09:00:00")

    # 2️⃣ BREAK START
    call_api("2026-01-11T13:00:00")

    # 3️⃣ BREAK END
    call_api("2026-01-11T13:30:00")

    # 4️⃣ CHECK-OUT (AFTER SHIFT → OT)
    call_api("2026-01-11T20:00:00")

    print("\n🎉 TEST COMPLETE")


if __name__ == "__main__":
    run_test()
