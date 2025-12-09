import pytest
from unittest.mock import MagicMock, patch
from datetime import date, time

def test_list_shifts(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = {"count": 10}
    mock_cursor.fetchall.return_value = [{"shift_id": 1, "shift_name": "Morning"}]
    
    response = client.get("/hrms/shifts/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 10
    assert len(data["data"]) == 1

def test_roster(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchall.return_value = [{"employee_id": 1, "shift_name": "Morning"}]
    
    response = client.get("/hrms/shifts/roster")
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_get_shift_employees(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchall.return_value = [{"employee_id": 1, "first_name": "John"}]
    
    response = client.get("/hrms/shifts/1/employees")
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_create_shift(client):
    payload = {
        "shift_name": "Morning",
        "start_time": "09:00:00",
        "end_time": "18:00:00"
    }
    with patch("app.api.shifts.ShiftDB.add_shift") as mock_add:
        mock_add.return_value = {"shift_id": 1, **payload}
        response = client.post("/hrms/shifts/", json=payload)
        assert response.status_code == 200
        assert response.json()["shift_id"] == 1

def test_get_shift(client):
    with patch("app.api.shifts.ShiftDB.get_one") as mock_get:
        mock_get.return_value = {"shift_id": 1, "shift_name": "Morning"}
        response = client.get("/hrms/shifts/1")
        assert response.status_code == 200
        assert response.json()["shift_name"] == "Morning"

def test_update_shift(client):
    payload = {
        "shift_name": "Evening",
        "start_time": "14:00:00",
        "end_time": "22:00:00"
    }
    with patch("app.api.shifts.ShiftDB.get_one") as mock_get:
        mock_get.return_value = {"shift_id": 1}
        with patch("app.api.shifts.ShiftDB.update_shift") as mock_update:
            mock_update.return_value = {"shift_id": 1, **payload}
            response = client.put("/hrms/shifts/1", json=payload)
            assert response.status_code == 200
            assert response.json()["shift_name"] == "Evening"

def test_delete_shift(client):
    with patch("app.api.shifts.ShiftDB.delete_shift") as mock_delete:
        mock_delete.return_value = True
        response = client.delete("/hrms/shifts/1")
        assert response.status_code == 200
        assert "archived successfully" in response.json()["message"]

def test_assign_shift(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    
    with patch("app.api.shifts.EmployeeDB.get_one") as mock_emp:
        mock_emp.return_value = {"id": 1}
        with patch("app.api.shifts.ShiftDB.get_one") as mock_shift:
            mock_shift.return_value = {"id": 1}
            
            mock_cursor.fetchone.return_value = {"id": 1} # For returning *
            
            payload = {
                "employee_id": 1,
                "shift_id": 1,
                "effective_from": "2023-01-01"
            }
            response = client.post("/hrms/shifts/assign", json=payload)
            assert response.status_code == 200
            assert "assigned successfully" in response.json()["message"]

def test_unassign_shift(client, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.rowcount = 1
    
    response = client.delete("/hrms/shifts/unassign/1")
    assert response.status_code == 200
    assert "unassigned successfully" in response.json()["message"]

def test_shift_history(client):
    with patch("app.api.shifts.EmployeeShiftDB.get_shift_history") as mock_hist:
        mock_hist.return_value = []
        response = client.get("/hrms/shifts/history/1")
        assert response.status_code == 200
        assert response.json() == []
