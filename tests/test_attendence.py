import pytest
from unittest.mock import MagicMock, patch
from datetime import date

def test_check_in(client):
    with patch("app.services.attendence_services.AttendanceService.check_in") as mock_check_in:
        mock_check_in.return_value = {"status": "checked_in"}
        response = client.post("/hrms/attendance/check-in", json={"employee_id": 1})
        assert response.status_code == 200
        assert response.json() == {"status": "checked_in"}
        mock_check_in.assert_called_once_with(1, "manual", None)

def test_check_out(client):
    with patch("app.services.attendence_services.AttendanceService.check_out") as mock_check_out:
        mock_check_out.return_value = {"status": "checked_out"}
        response = client.post("/hrms/attendance/check-out", json={"employee_id": 1})
        assert response.status_code == 200
        assert response.json() == {"status": "checked_out"}
        mock_check_out.assert_called_once_with(1, "manual", None)

def test_today_status(client):
    with patch("app.database.attendence.AttendanceDB.get_by_employee_and_date") as mock_get:
        mock_get.return_value = {"status": "present"}
        response = client.get("/hrms/attendance/today/1")
        assert response.status_code == 200
        assert response.json() == {"status": "present"}

def test_company_attendance(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchall.return_value = [{"employee_id": 1, "first_name": "John"}]
    
    response = client.get("/hrms/attendance/company")
    assert response.status_code == 200
    assert response.json() == [{"employee_id": 1, "first_name": "John"}]

def test_late_report(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchall.return_value = [{"employee_id": 1, "is_late": True}]
    
    response = client.get(f"/hrms/attendance/reports/late?start_date={date.today()}&end_date={date.today()}")
    assert response.status_code == 200
    assert response.json() == [{"employee_id": 1, "is_late": True}]

def test_lock_attendance(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    
    response = client.post(f"/hrms/attendance/lock/1?dt={date.today()}")
    assert response.status_code == 200
    assert response.json() == {"message": "Attendance locked"}
    mock_conn.commit.assert_called_once()

def test_override_attendance_success(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = {"id": 1, "status": "Present"}
    
    payload = {
        "check_in": "09:00",
        "check_out": "18:00",
        "status": "Present"
    }
    response = client.put(f"/hrms/attendance/override/1?dt={date.today()}", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Attendance overridden successfully"
    mock_conn.commit.assert_called_once()

def test_override_attendance_locked(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = None # Simulate locked or not found
    
    payload = {
        "check_in": "09:00"
    }
    response = client.put(f"/hrms/attendance/override/1?dt={date.today()}", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Attendance is locked or record not found"
