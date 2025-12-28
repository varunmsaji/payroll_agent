import pytest
from unittest.mock import MagicMock, patch
from datetime import date

def test_dashboard_overview(client):
    today = date.today()
    
    # Mock fetch_one and fetch_all
    with patch("app.api.dashboard_api.fetch_one") as mock_fetch_one:
        with patch("app.api.dashboard_api.fetch_all") as mock_fetch_all:
            
            # Define side effects for fetch_one
            def fetch_one_side_effect(sql, params=None):
                if "employees" in sql:
                    return (10, 8) # total, active
                if "is_late" in sql:
                    return (5, 2, 1) # present, absent, late
                if "overtime_minutes" in sql:
                    return (2.5,) # total_overtime_hours
                return None
            
            mock_fetch_one.side_effect = fetch_one_side_effect
            
            # Define side effects for fetch_all
            def fetch_all_side_effect(sql, params=None):
                if "employee_shifts" in sql:
                    return [("Morning", 5), ("Evening", 3)]
                if "attendance_events" in sql:
                    return [(1, "John Doe", "check-in", "09:00", "manual")]
                return []
            
            mock_fetch_all.side_effect = fetch_all_side_effect
            
            response = client.get("/hrms/admin/dashboard/overview")
            assert response.status_code == 200
            data = response.json()
            
            assert data["date"] == str(today)
            assert data["employees"] == {"total": 10, "active": 8}
            assert data["attendance_today"] == {"present": 5, "absent": 2, "late": 1}
            assert data["overtime_today_hours"] == 2.5
            assert data["shift_distribution"] == [
                {"shift_name": "Morning", "employees_assigned": 5},
                {"shift_name": "Evening", "employees_assigned": 3}
            ]
            assert len(data["recent_activity"]) == 1
            assert data["recent_activity"][0]["employee_name"] == "John Doe"
