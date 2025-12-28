import pytest
from unittest.mock import MagicMock, patch
from datetime import date

def test_today_stats(client):
    today = date.today()
    
    # Mock EmployeeDB.get_all
    with patch("app.api.attendence_dashboard.EmployeeDB.get_all") as mock_get_all_emps:
        mock_get_all_emps.return_value = [
            {"employee_id": 1},
            {"employee_id": 2}
        ]
        
        # Mock AttendanceDB.get_attendance
        with patch("app.api.attendence_dashboard.AttendanceDB.get_attendance") as mock_get_att:
            # Employee 1 present, Employee 2 absent
            def side_effect(emp_id):
                if emp_id == 1:
                    return [{
                        "employee_id": 1,
                        "date": today,
                        "late_minutes": 10,
                        "overtime_minutes": 60,
                        "total_hours": 9.0
                    }]
                return []
            
            mock_get_att.side_effect = side_effect
            
            # Mock EmployeeShiftDB.get_current_shift
            with patch("app.api.attendence_dashboard.EmployeeShiftDB.get_current_shift") as mock_get_shift:
                mock_get_shift.return_value = {"shift_name": "Morning"}
                
                response = client.get("/hrms/dashboard/today-stats")
                assert response.status_code == 200
                data = response.json()
                
                assert data["total_employees"] == 2
                assert data["present_today"] == 1
                assert data["absent_today"] == 1
                assert data["late_today"] == 1
                assert data["overtime_today"] == 1.0
                assert data["total_hours_today"] == 9.0
                assert data["shift_wise"] == [{"shift_name": "Morning", "count": 1}]

def test_today_attendance_table(client):
    today = date.today()
    
    # Mock EmployeeDB.get_all
    with patch("app.api.attendence_dashboard.EmployeeDB.get_all") as mock_get_all_emps:
        mock_get_all_emps.return_value = [
            {"employee_id": 1, "first_name": "John", "last_name": "Doe"}
        ]
        
        # Mock AttendanceDB.get_attendance
        with patch("app.api.attendence_dashboard.AttendanceDB.get_attendance") as mock_get_att:
            mock_get_att.return_value = [{
                "date": today,
                "check_in": "09:00",
                "check_out": "18:00",
                "total_hours": 9.0,
                "late_minutes": 0,
                "overtime_minutes": 0
            }]
            
            # Mock EmployeeShiftDB.get_current_shift
            with patch("app.api.attendence_dashboard.EmployeeShiftDB.get_current_shift") as mock_get_shift:
                mock_get_shift.return_value = {"shift_name": "Morning"}
                
                response = client.get("/hrms/attendance/today")
                assert response.status_code == 200
                data = response.json()
                
                assert len(data) == 1
                assert data[0]["employee_id"] == 1
                assert data[0]["name"] == "John Doe"
                assert data[0]["shift"] == "Morning"
