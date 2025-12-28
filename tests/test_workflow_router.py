import pytest
from unittest.mock import MagicMock, patch

def test_create_workflow(client):
    payload = {
        "name": "Leave Workflow",
        "module": "leave",
        "steps": [
            {"step_order": 1, "role": "Manager", "is_final": False},
            {"step_order": 2, "role": "HR", "is_final": True}
        ]
    }
    with patch("app.api.workflow_router.workflow_db.create_workflow") as mock_create:
        mock_create.return_value = 1
        response = client.post("/workflow/create", json=payload)
        assert response.status_code == 200
        assert response.json()["workflow_id"] == 1

def test_list_workflows(client):
    with patch("app.api.workflow_router.workflow_db.get_all_workflows") as mock_list:
        mock_list.return_value = [{"id": 1, "name": "Leave Workflow"}]
        response = client.get("/workflow/all")
        assert response.status_code == 200
        assert len(response.json()) == 1

def test_get_workflow_details(client):
    with patch("app.api.workflow_router.workflow_db.get_workflow_by_id") as mock_get:
        mock_get.return_value = {"id": 1, "name": "Leave Workflow"}
        response = client.get("/workflow/by-id/1")
        assert response.status_code == 200
        assert response.json()["id"] == 1

def test_edit_workflow(client):
    payload = {
        "name": "Updated Workflow",
        "steps": []
    }
    with patch("app.api.workflow_router.workflow_db.update_workflow") as mock_update:
        response = client.put("/workflow/1", json=payload)
        assert response.status_code == 200
        assert "updated successfully" in response.json()["message"]

def test_activate_workflow(client):
    with patch("app.api.workflow_router.workflow_db.activate_workflow") as mock_activate:
        response = client.post("/workflow/activate/1")
        assert response.status_code == 200
        assert "activated" in response.json()["message"]

def test_start_workflow(client):
    payload = {"employee_id": 1}
    with patch("app.api.workflow_router.workflow_db.get_active_workflow") as mock_get:
        mock_get.return_value = {"id": 1}
        with patch("app.api.workflow_router.workflow_db.start_workflow") as mock_start:
            mock_start.return_value = {"status": "started"}
            response = client.post("/workflow/leave/start/100", json=payload)
            assert response.status_code == 200
            assert response.json()["status"] == "started"

def test_approve_step(client):
    payload = {"approver_id": 2, "remarks": "Approved"}
    with patch("app.api.workflow_router.workflow_db.approve_step") as mock_approve:
        mock_approve.return_value = {"status": "approved"}
        response = client.post("/workflow/leave/100/approve", json=payload)
        assert response.status_code == 200
        assert response.json()["result"]["status"] == "approved"

def test_reject_step(client):
    payload = {"approver_id": 2, "remarks": "Rejected"}
    with patch("app.api.workflow_router.workflow_db.reject_step") as mock_reject:
        response = client.post("/workflow/leave/100/reject", json=payload)
        assert response.status_code == 200
        assert "Rejected" in response.json()["message"]

def test_get_status(client):
    with patch("app.api.workflow_router.workflow_db.get_workflow_status") as mock_status:
        mock_status.return_value = {"status": "pending"}
        response = client.get("/workflow/leave/100")
        assert response.status_code == 200
        assert response.json()["status"] == "pending"
