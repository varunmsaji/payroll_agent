import pytest
from unittest.mock import MagicMock, patch
from datetime import date

def test_employee_profile(client):
    with patch("app.api.employee_detail.EmployeeDB.get_one") as mock_get:
        mock_get.return_value = {"employee_id": 1, "first_name": "John"}
        response = client.get("/hrms/employee/1")
        assert response.status_code == 200
        assert response.json() == {"employee_id": 1, "first_name": "John"}

def test_employee_profile_not_found(client):
    with patch("app.api.employee_detail.EmployeeDB.get_one") as mock_get:
        mock_get.return_value = None
        response = client.get("/hrms/employee/999")
        assert response.status_code == 404

def test_get_employees(client):
    with patch("app.api.employee_detail.EmployeeDB.get_all") as mock_get_all:
        mock_get_all.return_value = [{"id": 1}, {"id": 2}]
        response = client.get("/hrms/employees?page=1&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["data"]) == 2

def test_assign_manager(client):
    with patch("app.api.employee_detail.EmployeeDB.get_one") as mock_get:
        mock_get.side_effect = lambda id: {"id": id} if id in [1, 2] else None
        
        with patch("app.api.employee_detail.EmployeeDB.set_manager") as mock_set:
            mock_set.return_value = {"id": 1, "manager_id": 2}
            
            response = client.put("/hrms/employee/1/manager", json={"manager_id": 2})
            assert response.status_code == 200
            assert response.json()["message"] == "Manager assigned successfully"

def test_employee_shift(client):
    with patch("app.api.employee_detail.EmployeeShiftDB.get_current_shift") as mock_get:
        mock_get.return_value = {"shift_name": "Morning"}
        response = client.get("/hrms/employee/1/shift")
        assert response.status_code == 200
        assert response.json() == {"shift_name": "Morning"}

def test_attendance_summary(client):
    today = date.today()
    with patch("app.api.employee_detail.AttendanceDB.get_attendance") as mock_get:
        mock_get.return_value = [
            {"date": today, "total_hours": 8.0},
            {"date": date(2023, 1, 1), "total_hours": 8.0}
        ]
        response = client.get("/hrms/employee/1/attendance-summary")
        assert response.status_code == 200
        data = response.json()
        assert data["today"]["total_hours"] == 8.0
        assert data["total_hours_last_30_days"] == 16.0

def test_full_employee_details(client):
    with patch("app.api.employee_detail.EmployeeDB.get_one") as mock_emp:
        mock_emp.return_value = {"id": 1}
        with patch("app.api.employee_detail.EmployeeShiftDB.get_current_shift") as mock_shift:
            mock_shift.return_value = {}
            with patch("app.api.employee_detail.attendance_summary") as mock_att_sum: # Patching the function directly might be tricky if it's imported or local
                # Since attendance_summary is defined in the same file, we might need to patch where it's used or rely on its internal mocks.
                # However, since we are testing the router, we can mock the DB calls it makes.
                # But to simplify, let's just mock the DB calls for all sub-functions.
                
                with patch("app.api.employee_detail.AttendanceDB.get_attendance") as mock_att:
                    mock_att.return_value = []
                    with patch("app.api.employee_detail.AttendanceEventDB.get_all_events_for_employee") as mock_events:
                        mock_events.return_value = []
                        with patch("app.api.employee_detail.SalaryDB.get_salary_structure") as mock_salary:
                            mock_salary.return_value = {}
                            with patch("app.api.employee_detail.PayrollDB.get_payroll") as mock_payroll:
                                mock_payroll.return_value = {}
                                
                                response = client.get("/hrms/employee/1/full-details")
                                assert response.status_code == 200
                                assert "profile" in response.json()
