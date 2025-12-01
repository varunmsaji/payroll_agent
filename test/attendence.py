import requests
from datetime import date
import time

# ============================
# CONFIG (EDIT THIS)
# ============================

BASE_URL = "http://127.0.0.1:8000/hrms/attendance"

EMPLOYEE_ID = 35   # 🔴 Change to a real employee ID in your DB
MANAGER_ID = 27    # 🔴 Change to a real manager ID

TODAY = date.today().isoformat()


# ============================
# EMPLOYEE ACTION TESTS
# ============================

def test_check_in():
    print("\n🟢 TEST: CHECK-IN")
    url = f"{BASE_URL}/check-in"
    payload = {
        "employee_id": EMPLOYEE_ID,
        "source": "manual",
        "meta": {"device": "browser"}
    }

    res = requests.post(url, json=payload)
    print(res.status_code, res.json())


def test_break_start():
    print("\n🟡 TEST: BREAK START")
    url = f"{BASE_URL}/break/start"
    payload = {
        "employee_id": EMPLOYEE_ID,
        "source": "manual"
    }

    res = requests.post(url, json=payload)
    print(res.status_code, res.json())


def test_break_end():
    print("\n🟡 TEST: BREAK END")
    url = f"{BASE_URL}/break/end"
    payload = {
        "employee_id": EMPLOYEE_ID,
        "source": "manual"
    }

    res = requests.post(url, json=payload)
    print(res.status_code, res.json())


def test_check_out():
    print("\n🔴 TEST: CHECK-OUT")
    url = f"{BASE_URL}/check-out"
    payload = {
        "employee_id": EMPLOYEE_ID,
        "source": "manual"
    }

    res = requests.post(url, json=payload)
    print(res.status_code, res.json())


# ============================
# DASHBOARD TESTS
# ============================

def test_today_status():
    print("\n📊 TEST: TODAY STATUS")
    url = f"{BASE_URL}/today/{EMPLOYEE_ID}"
    res = requests.get(url)
    print(res.status_code)
    print(res.json())


def test_employee_attendance():
    print("\n📅 TEST: EMPLOYEE MONTHLY ATTENDANCE")
    url = f"{BASE_URL}/employee/{EMPLOYEE_ID}"
    params = {
        "start_date": "2025-01-01",
        "end_date": TODAY
    }

    res = requests.get(url, params=params)
    print(res.status_code)
    for row in res.json():
        print(row)


def test_team_attendance():
    print("\n👥 TEST: TEAM ATTENDANCE (MANAGER VIEW)")
    url = f"{BASE_URL}/team/{MANAGER_ID}"
    params = {"date": TODAY}

    res = requests.get(url, params=params)
    print(res.status_code)
    for row in res.json():
        print(row)


def test_company_attendance():
    print("\n🏢 TEST: COMPANY DAILY ATTENDANCE (HR VIEW)")
    url = f"{BASE_URL}/company"
    params = {"date_": TODAY}

    res = requests.get(url, params=params)
    print(res.status_code)
    for row in res.json():
        print(row)


# ============================
# REPORTS TESTS
# ============================

def test_late_report():
    print("\n⏰ TEST: LATE REPORT")
    url = f"{BASE_URL}/reports/late"
    params = {
        "start_date": "2025-01-01",
        "end_date": TODAY
    }

    res = requests.get(url, params=params)
    print(res.status_code)
    for row in res.json():
        print(row)


def test_overtime_report():
    print("\n⏳ TEST: OVERTIME REPORT")
    url = f"{BASE_URL}/reports/overtime"
    params = {
        "start_date": "2025-01-01",
        "end_date": TODAY
    }

    res = requests.get(url, params=params)
    print(res.status_code)
    for row in res.json():
        print(row)


# ============================
# RAW LOGS TEST
# ============================

def test_raw_logs():
    print("\n📜 TEST: RAW ATTENDANCE LOGS")
    url = f"{BASE_URL}/logs/{EMPLOYEE_ID}"
    res = requests.get(url)

    print(res.status_code)
    for row in res.json():
        print(row)


# ============================
# PAYROLL LOCK / UNLOCK
# ============================

def test_lock():
    print("\n🔒 TEST: PAYROLL LOCK")
    url = f"{BASE_URL}/lock/{EMPLOYEE_ID}"
    params = {"dt": TODAY}

    res = requests.post(url, params=params)
    print(res.status_code, res.json())


def test_unlock():
    print("\n🔓 TEST: PAYROLL UNLOCK")
    url = f"{BASE_URL}/unlock/{EMPLOYEE_ID}"
    params = {"dt": TODAY}

    res = requests.post(url, params=params)
    print(res.status_code, res.json())


# ============================
# HR MANUAL OVERRIDE
# ============================

def test_override():
    print("\n✏️ TEST: HR MANUAL OVERRIDE")
    url = f"{BASE_URL}/override/{EMPLOYEE_ID}"
    params = {"dt": TODAY}

    payload = {
        "check_in": "09:00",
        "check_out": "18:00",
        "net_hours": 8.5,
        "status": "present"
    }

    res = requests.put(url, params=params, json=payload)
    print(res.status_code, res.json())


# ============================
# MAIN RUNNER
# ============================

if __name__ == "__main__":

    print("\n==============================")
    print("🚀 STARTING ATTENDANCE API TEST")
    print("==============================")

    test_check_in()
    time.sleep(2)

    test_break_start()
    time.sleep(2)

    test_break_end()
    time.sleep(2)

    test_check_out()
    time.sleep(2)

    test_today_status()

    test_employee_attendance()

    test_team_attendance()

    test_company_attendance()

    test_late_report()

    test_overtime_report()

    test_raw_logs()

    test_lock()

    test_override()

    test_unlock()

    print("\n✅✅✅ ALL TESTS COMPLETED ✅✅✅")
