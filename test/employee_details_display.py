import requests
import json

BASE_URL = "http://127.0.0.1:8000"
EMPLOYEE_ID = 35


def pretty(title, res):
    print("\n" + "=" * 100)
    print(f"🔹 {title}")
    print("Status:", res.status_code)
    try:
        print(json.dumps(res.json(), indent=2, default=str))
    except:
        print(res.text)
    print("=" * 100)


# ✅ 1️⃣ EMPLOYEE LIST
def test_employee_list_ui():
    url = f"{BASE_URL}/hrms/employees"
    params = {"page": 1, "limit": 20}
    res = requests.get(url, params=params)
    pretty("EMPLOYEE UI LIST", res)


def test_employee_profile():
    url = f"{BASE_URL}/hrms/employee/{EMPLOYEE_ID}"
    res = requests.get(url)
    pretty("EMPLOYEE PROFILE", res)


def test_managers():
    url = f"{BASE_URL}/hrms/employees/managers"
    res = requests.get(url)
    pretty("MANAGERS", res)


def test_assign_manager():
    url = f"{BASE_URL}/hrms/employee/{EMPLOYEE_ID}/manager"
    payload = {"manager_id": None}
    res = requests.put(url, json=payload)
    pretty("MANAGER UPDATED", res)


def test_shift():
    url = f"{BASE_URL}/hrms/employee/{EMPLOYEE_ID}/shift"
    res = requests.get(url)
    pretty("SHIFT DETAILS", res)


def test_attendance_summary():
    url = f"{BASE_URL}/hrms/employee/{EMPLOYEE_ID}/attendance-summary"
    res = requests.get(url)
    pretty("ATTENDANCE SUMMARY", res)


def test_time_summary():
    url = f"{BASE_URL}/hrms/employee/{EMPLOYEE_ID}/time-summary"
    res = requests.get(url)
    pretty("TIME SUMMARY", res)


def test_events():
    url = f"{BASE_URL}/hrms/employee/{EMPLOYEE_ID}/events"
    res = requests.get(url)
    pretty("ATTENDANCE EVENTS", res)


def test_salary():
    url = f"{BASE_URL}/hrms/employee/{EMPLOYEE_ID}/salary"
    res = requests.get(url)
    pretty("SALARY STRUCTURE", res)


def test_latest_payroll():
    url = f"{BASE_URL}/hrms/employee/{EMPLOYEE_ID}/payroll/latest"
    res = requests.get(url)
    pretty("LATEST PAYROLL", res)


def test_payroll_history():
    url = f"{BASE_URL}/hrms/employee/{EMPLOYEE_ID}/payroll-history"
    res = requests.get(url)
    pretty("PAYROLL HISTORY", res)


def test_full_employee_dashboard():
    url = f"{BASE_URL}/hrms/employee/{EMPLOYEE_ID}/full-details"
    res = requests.get(url)
    pretty("FULL DASHBOARD", res)


def test_employee_leaves():
    url = f"{BASE_URL}/hrms/leaves/history/{EMPLOYEE_ID}"
    res = requests.get(url)
    pretty("LEAVE HISTORY", res)


def test_leave_balance():
    url = f"{BASE_URL}/hrms/employee/{EMPLOYEE_ID}/leave-balance"
    res = requests.get(url)
    pretty("LEAVE BALANCE", res)


if __name__ == "__main__":
    print("\n🚀 STARTING FULL EMPLOYEE DISPLAY UI API TEST SUITE")

    test_employee_list_ui()
    test_employee_profile()
    test_managers()
    test_assign_manager()
    test_shift()
    test_attendance_summary()
    test_time_summary()
    test_events()
    test_salary()
    test_latest_payroll()
    test_payroll_history()
    test_full_employee_dashboard()
    test_employee_leaves()
    test_leave_balance()

    print("\n✅ ALL EMPLOYEE DISPLAY API TESTS COMPLETED SUCCESSFULLY ✅")
