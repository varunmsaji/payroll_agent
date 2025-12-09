import pytest
from unittest.mock import MagicMock, patch

def test_get_payroll_policy(client):
    with patch("app.api.settings.PayrollPolicyDB.get_active_policy") as mock_get:
        mock_get.return_value = {"overtime_enabled": True}
        response = client.get("/hrms/settings/payroll-policy")
        assert response.status_code == 200
        assert response.json() == {"overtime_enabled": True}

def test_update_payroll_policy(client):
    payload = {
        "late_grace_minutes": 15,
        "late_lop_threshold_minutes": 30,
        "early_exit_grace_minutes": 15,
        "early_exit_lop_threshold_minutes": 30,
        "overtime_enabled": True,
        "overtime_multiplier": 1.5,
        "holiday_double_pay": True,
        "weekend_paid_only_if_worked": False,
        "night_shift_allowance": 100.0
    }
    with patch("app.api.settings.PayrollPolicyDB.update_policy") as mock_update:
        mock_update.return_value = payload
        response = client.put("/hrms/settings/payroll-policy", json=payload)
        assert response.status_code == 200
        assert response.json()["policy"]["late_grace_minutes"] == 15

def test_get_attendance_policy(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = {"late_grace_minutes": 10}
    
    response = client.get("/hrms/settings/attendance-policy")
    assert response.status_code == 200
    assert response.json() == {"late_grace_minutes": 10}

def test_update_attendance_policy(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = {"late_grace_minutes": 20}
    
    payload = {
        "late_grace_minutes": 20,
        "early_exit_grace_minutes": 20,
        "full_day_fraction": 0.8,
        "half_day_fraction": 0.5,
        "night_shift_enabled": True,
        "overtime_enabled": True
    }
    response = client.put("/hrms/settings/attendance-policy", json=payload)
    assert response.status_code == 200
    assert response.json()["policy"]["late_grace_minutes"] == 20

def test_list_workflows(client):
    with patch("app.api.settings.workflow_db.get_all_workflows") as mock_get:
        mock_get.return_value = [{"id": 1, "name": "Leave Workflow"}]
        response = client.get("/hrms/settings/workflows")
        assert response.status_code == 200
        assert response.json() == [{"id": 1, "name": "Leave Workflow"}]

def test_activate_workflow(client):
    with patch("app.api.settings.workflow_db.activate_workflow") as mock_activate:
        response = client.post("/hrms/settings/workflows/activate", json={"workflow_id": 1})
        assert response.status_code == 200
        assert "activated successfully" in response.json()["message"]
        mock_activate.assert_called_once_with(1)

def test_deactivate_workflow(client):
    with patch("app.api.settings.workflow_db.deactivate_workflow") as mock_deactivate:
        response = client.post("/hrms/settings/workflows/deactivate", json={"workflow_id": 1})
        assert response.status_code == 200
        assert "deactivated successfully" in response.json()["message"]
        mock_deactivate.assert_called_once_with(1)
