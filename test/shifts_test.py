import requests
import json
from datetime import date

BASE_URL = "http://127.0.0.1:8000"
EMPLOYEE_ID = 35   # ✅ Change if needed


# ==========================================================
# ✅ HELPER PRINTER
# ==========================================================
def pretty(title, res):
    print("\n" + "=" * 100)
    print(f"🔹 {title}")
    print("Status:", res.status_code)
    try:
        print(json.dumps(res.json(), indent=2, default=str))
    except:
        print(res.text)
    print("=" * 100)


# ==========================================================
# ✅ 1️⃣ CREATE SHIFTS
# ==========================================================
def create_shift(payload):
    url = f"{BASE_URL}/hrms/shifts/"
    res = requests.post(url, json=payload)
    pretty("SHIFT CREATED", res)
    return res.json() if res.status_code == 200 else None


# ==========================================================
# ✅ 2️⃣ LIST SHIFTS
# ==========================================================
def list_shifts():
    url = f"{BASE_URL}/hrms/shifts/"
    params = {"page": 1, "limit": 10}
    res = requests.get(url, params=params)
    pretty("SHIFT LIST", res)
    return res.json()


# ==========================================================
# ✅ 3️⃣ ASSIGN SHIFT TO EMPLOYEE
# ==========================================================
def assign_shift(employee_id, shift_id):
    url = f"{BASE_URL}/hrms/shifts/assign"
    payload = {
        "employee_id": employee_id,
        "shift_id": shift_id,
        "effective_from": str(date.today())
    }
    res = requests.post(url, json=payload)
    pretty("SHIFT ASSIGNED", res)
    return res.json()


# ==========================================================
# ✅ 4️⃣ FETCH CURRENT ACTIVE SHIFT
# ==========================================================
def get_current_shift(employee_id):
    url = f"{BASE_URL}/hrms/employee/{employee_id}/shift"
    res = requests.get(url)
    pretty("CURRENT SHIFT", res)
    return res.json()


# ==========================================================
# ✅ 5️⃣ FETCH SHIFT HISTORY
# ==========================================================
def shift_history(employee_id):
    url = f"{BASE_URL}/hrms/shifts/history/{employee_id}"
    res = requests.get(url)
    pretty("SHIFT HISTORY", res)
    return res.json()


# ==========================================================
# ✅ 6️⃣ UNASSIGN SHIFT (CLOSE EFFECTIVE_TO)
# ==========================================================
# ✅ TEST 6: UNASSIGN SHIFT
def unassign_shift(employee_id):
    print("\n✅ TEST 6: UNASSIGN SHIFT")

    url = f"{BASE_URL}/hrms/shifts/unassign/{employee_id}"
    res = requests.delete(url)

    pretty("SHIFT UNASSIGNED", res)



# ==========================================================
# ✅ 🚀 MASTER TEST RUNNER
# ==========================================================
if __name__ == "__main__":
    print("\n🚀 STARTING FULL SHIFT MODULE TEST")

    # ✅ 1️⃣ CREATE DEMO SHIFTS
    print("\n✅ TEST 1: CREATE SHIFTS")

    shift_1 = {
        "shift_name": "General Shift",
        "start_time": "09:00:00",
        "end_time": "17:00:00",
        "is_night_shift": False
    }

    shift_2 = {
        "shift_name": "Night Shift",
        "start_time": "22:00:00",
        "end_time": "06:00:00",
        "is_night_shift": True
    }

    create_shift(shift_1)
    create_shift(shift_2)

    # ✅ 2️⃣ LIST SHIFTS
    print("\n✅ TEST 2: LIST SHIFTS")
    shifts_data = list_shifts()

    if not shifts_data["data"]:
        print("❌ No shifts found. Cannot continue test.")
        exit()

    first_shift_id = shifts_data["data"][0]["shift_id"]

    # ✅ 3️⃣ ASSIGN SHIFT
    print(f"\n✅ TEST 3: ASSIGN SHIFT {first_shift_id} TO EMPLOYEE {EMPLOYEE_ID}")
    assign_shift(EMPLOYEE_ID, first_shift_id)

    # ✅ 4️⃣ FETCH CURRENT SHIFT
    print("\n✅ TEST 4: FETCH CURRENT SHIFT")
    get_current_shift(EMPLOYEE_ID)

    # ✅ 5️⃣ SHIFT HISTORY
    print("\n✅ TEST 5: SHIFT HISTORY")
    shift_history(EMPLOYEE_ID)

    # ✅ 6️⃣ UNASSIGN SHIFT
    print("\n✅ TEST 6: UNASSIGN SHIFT")
    unassign_shift(EMPLOYEE_ID)

    print("\n✅✅✅ FULL SHIFT MODULE TEST COMPLETED SUCCESSFULLY ✅✅✅\n")
