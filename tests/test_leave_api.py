import pytest
from unittest.mock import MagicMock, patch
from datetime import date

def test_add_leave_type(client):
    with patch("app.api.leave_api.LeaveTypeDB.add_leave_type") as mock_add:
        mock_add.return_value = {"id": 1, "name": "Sick Leave"}
        response = client.post("/hrms/leaves/types", json={"name": "Sick Leave", "code": "SL"})
        assert response.status_code == 200
        assert response.json() == {"id": 1, "name": "Sick Leave"}

def test_get_leave_types(client):
    with patch("app.api.leave_api.LeaveTypeDB.get_leave_types") as mock_get:
        mock_get.return_value = [{"id": 1, "name": "Sick Leave"}]
        response = client.get("/hrms/leaves/types")
        assert response.status_code == 200
        assert len(response.json()) == 1

def test_initialize_balance(client):
    with patch("app.api.leave_api.LeaveBalanceDB.initialize_balance") as mock_init:
        mock_init.return_value = {"id": 1}
        payload = {"employee_id": 1, "leave_type_id": 1, "year": 2023, "quota": 10}
        response = client.post("/hrms/leaves/balance/init", json=payload)
        assert response.status_code == 200
        assert response.json() == {"id": 1}

def test_apply_leave_success(client):
    payload = {
        "employee_id": 1,
        "leave_type_id": 1,
        "start_date": "2023-01-01",
        "end_date": "2023-01-02",
        "total_days": 2,
        "reason": "Sick"
    }
    
    with patch("app.api.leave_api.LeaveBalanceDB.get_single_balance") as mock_balance:
        mock_balance.return_value = {"remaining_quota": 5}
        
        with patch("app.api.leave_api.LeaveRequestDB.has_overlapping_approved_leave") as mock_overlap:
            mock_overlap.return_value = False
            
            with patch("app.api.leave_api.LeaveRequestDB.apply_leave") as mock_apply:
                mock_apply.return_value = {"leave_id": 100}
                
                with patch("app.api.leave_api.workflow_db.get_active_workflow") as mock_wf:
                    mock_wf.return_value = {"id": 1}
                    with patch("app.api.leave_api.workflow_db.start_workflow") as mock_start_wf:
                        
                        response = client.post("/hrms/leaves/apply", json=payload)
                        assert response.status_code == 200
                        assert response.json()["message"] == "Leave applied successfully"

def test_apply_leave_insufficient_balance(client):
    payload = {
        "employee_id": 1,
        "leave_type_id": 1,
        "start_date": "2023-01-01",
        "end_date": "2023-01-05",
        "total_days": 5,
        "reason": "Sick"
    }
    
    with patch("app.api.leave_api.LeaveBalanceDB.get_single_balance") as mock_balance:
        mock_balance.return_value = {"remaining_quota": 2} # Less than requested
        
        response = client.post("/hrms/leaves/apply", json=payload)
        assert response.status_code == 400
        assert "Insufficient leave balance" in response.json()["detail"]

def test_get_requests(client):
    with patch("app.api.leave_api.LeaveRequestDB.list_requests") as mock_list:
        mock_list.return_value = []
        response = client.get("/hrms/leaves/requests")
        assert response.status_code == 200
        assert response.json() == []

def test_calculate_salary_after_leaves(client):
    with patch("app.api.leave_api.EmployeeSalaryDB.get_base_salary") as mock_base:
        mock_base.return_value = {"base_salary": 3000}
        
        with patch("app.api.leave_api.LeaveHistoryDB.get_unpaid_leave_days") as mock_unpaid:
            mock_unpaid.return_value = 2
            
            response = client.get("/hrms/leaves/salary/1/2023/1")
            assert response.status_code == 200
            data = response.json()
            # 3000 / 30 = 100 per day. 2 unpaid days = 200 deduction. Final = 2800.
            assert data["base_salary"] == 3000.0
            assert data["deduction"] == 200.0
            assert data["final_salary"] == 2800.0

def test_leave_admin_stats(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    
    # Mock return values for 3 queries
    mock_cursor.fetchone.side_effect = [
        {"total": 10, "pending": 2, "approved": 5, "rejected": 3}, # Overall
        {"this_month": 4}, # Monthly
        {"paid_leaves": 8, "unpaid_leaves": 2} # Paid stats
    ]
    
    response = client.get("/hrms/leaves/admin/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_requests"] == 10
    assert data["this_month_requests"] == 4
    assert data["paid_leaves"] == 8

def test_admin_approve_leave(client):
    with patch("app.api.leave_api.LeaveRequestDB.update_leave_status_only") as mock_update:
        mock_update.return_value = {"id": 1, "status": "approved"}
        response = client.post("/hrms/leaves/admin/approve/1")
        assert response.status_code == 200
        assert response.json()["message"] == "Leave approved"
