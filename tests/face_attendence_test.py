import requests
import json
import time

BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/faces/attendance"

EMPLOYEE_EMAIL = "mock@company.com"

IMAGE_PATH = "test.jpeg"  # any valid image file

def call_api(label):
    with open(IMAGE_PATH, "rb") as img:
        response = requests.post(
            ENDPOINT,
            files={"image": img},
            data={
                "latitude": 12.97,
                "longitude": 77.59,
            },
            timeout=10,
        )

    print(f"\n🧪 {label}")
    print("Status:", response.status_code)

    try:
        data = response.json()
        print(json.dumps(data, indent=2))
        return data
    except Exception:
        print(response.text)
        return None


def reset_db():
    """Manual reminder – run this in SQL before test"""
    print("""
⚠️ MAKE SURE DB IS CLEAN BEFORE TEST:
-----------------------------------
DELETE FROM attendance_events WHERE employee_id = 36;
DELETE FROM attendance WHERE employee_id = 36;
-----------------------------------
""")


def run_happy_path():
    print("\n==============================")
    print("✅ TEST 1: HAPPY PATH")
    print("==============================")

    call_api("1️⃣ CHECK IN")
    call_api("2️⃣ BREAK START")
    call_api("3️⃣ BREAK END")
    call_api("4️⃣ CHECK OUT")


def run_edge_cases():
    print("\n==============================")
    print("⚠️ TEST 2: EDGE CASES")
    print("==============================")

    print("\n❌ CASE 1: CHECK OUT WITHOUT CHECK IN")
    call_api("INVALID ACTION")

    print("\n❌ CASE 2: DOUBLE CHECK IN")
    call_api("CHECK IN")
    call_api("DOUBLE CHECK IN")

    print("\n❌ CASE 3: DOUBLE BREAK START")
    call_api("BREAK START")
    call_api("DOUBLE BREAK START")

    print("\n❌ CASE 4: BREAK END WITHOUT BREAK")
    call_api("BREAK END WITHOUT BREAK")

    print("\n❌ CASE 5: CHECK OUT TWICE")
    call_api("CHECK OUT")
    call_api("DOUBLE CHECK OUT")


def run_final_state_check():
    print("\n==============================")
    print("📊 FINAL EXPECTED DB STATE")
    print("==============================")

    print("""
EXPECTED attendance_events ORDER:
---------------------------------
check_in
break_start
break_end
check_out

EXPECTED attendance.status:
---------------------------------
present OR half_day (policy dependent)

EXPECTED:
---------------------------------
is_payroll_locked = false
""")


if __name__ == "__main__":
    reset_db()
    input("Press ENTER once DB is cleaned...")

    run_happy_path()
    run_edge_cases()
    run_final_state_check()
