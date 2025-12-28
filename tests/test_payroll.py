import pytest
from unittest.mock import MagicMock, patch

def test_get_active_policy(client):
    with patch("app.api.payroll.PayrollPolicyDB.get_active_policy") as mock_get:
        mock_get.return_value = {"overtime_enabled": True}
        response = client.get("/hrms/payroll/policy")
        assert response.status_code == 200
        assert response.json() == {"overtime_enabled": True}

def test_update_policy(client):
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
    with patch("app.api.payroll.PayrollPolicyDB.update_policy") as mock_update:
        mock_update.return_value = payload
        response = client.put("/hrms/payroll/policy", json=payload)
        assert response.status_code == 200
        assert response.json()["late_grace_minutes"] == 15

def test_lock_payroll(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    # Mock _ensure_payroll_lock_table (implicit via get_connection)
    # Mock _set_period_lock execution
    
    response = client.post("/hrms/payroll/lock", json={"year": 2023, "month": 1, "lock": True})
    assert response.status_code == 200
    assert response.json()["locked"] is True

def test_generate_payroll_success(client):
    # Mock _is_period_locked to return False
    with patch("app.api.payroll._is_period_locked") as mock_locked:
        mock_locked.return_value = False
        
        with patch("app.api.payroll.PayrollService.generate_for_employee") as mock_gen:
            mock_gen.return_value = {"payroll": {"net_salary": 5000}}
            
            response = client.post("/hrms/payroll/generate", json={"employee_id": 1, "year": 2023, "month": 1})
            assert response.status_code == 200
            assert response.json()["payroll"]["net_salary"] == 5000

def test_generate_payroll_locked(client):
    with patch("app.api.payroll._is_period_locked") as mock_locked:
        mock_locked.return_value = True
        
        response = client.post("/hrms/payroll/generate", json={"employee_id": 1, "year": 2023, "month": 1})
        assert response.status_code == 400
        assert "Payroll is locked" in response.json()["detail"]

def test_generate_bulk_payroll(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    
    # Mock _is_period_locked
    with patch("app.api.payroll._is_period_locked") as mock_locked:
        mock_locked.return_value = False
        
        # Mock fetching active employees
        mock_cursor.fetchall.return_value = [(1,), (2,)]
        
        with patch("app.api.payroll.PayrollService.generate_for_employee") as mock_gen:
            mock_gen.return_value = {"payroll": {"net_salary": 5000}}
            
            response = client.post("/hrms/payroll/generate-bulk", json={"year": 2023, "month": 1})
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 2
            assert data["results"][0]["status"] == "success"

def test_get_employee_payroll(client):
    with patch("app.api.payroll.PayrollDB.get_payroll") as mock_get:
        mock_get.return_value = {"payroll_id": 1, "net_salary": 5000}
        response = client.get("/hrms/payroll/1?year=2023&month=1")
        assert response.status_code == 200
        assert response.json()["net_salary"] == 5000

def test_payroll_status(client):
    with patch("app.api.payroll.PayrollDB.get_payroll") as mock_get:
        mock_get.return_value = {"payroll_id": 1}
        response = client.get("/hrms/payroll/status/1?year=2023&month=1")
        assert response.status_code == 200
        assert response.json()["status"] == "generated"
