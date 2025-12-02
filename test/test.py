import requests
import json

# ======================================
# ✅ CONFIG
# ======================================

BASE_URL = "http://127.0.0.1:8000"   # Change if your server uses another port
EMPLOYEE_ID = 25                 # Change to test another employee


# ======================================
# ✅ TEST: EMPLOYEE LEAVE BALANCE
# ======================================

def test_leave_balance():
    print("\n==============================")
    print("🚀 TEST: EMPLOYEE LEAVE BALANCE")
    print("==============================\n")

    url = f"{BASE_URL}/hrms/employee/{EMPLOYEE_ID}/leave-balance"

    try:
        response = requests.get(url)

        print("🔹 STATUS CODE:", response.status_code)

        if response.status_code == 200:
            data = response.json()
            print("🔹 RESPONSE:\n")
            print(json.dumps(data, indent=4))

            if not data:
                print("\n⚠️ No leave balance assigned for this employee yet.")
            else:
                print("\n✅ Leave balance data loaded successfully!")

        else:
            print("❌ ERROR RESPONSE:")
            print(response.text)

    except Exception as e:
        print("❌ REQUEST FAILED:", str(e))


# ======================================
# ✅ RUN TEST
# ======================================

if __name__ == "__main__":
    test_leave_balance()
