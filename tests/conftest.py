import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import sys
import os
import psycopg2

# Add the project root to sys.path to allow imports from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.main import app
from app.database.connection import get_connection

@pytest.fixture
def mock_db_connection(monkeypatch):
    """
    Mocks the database connection to avoid using the real database during tests.
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    
    # Mock context manager behavior for the connection and cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None

    def mock_get_connection(*args, **kwargs):
        return mock_conn

    monkeypatch.setattr("psycopg2.connect", mock_get_connection)
    return mock_conn, mock_cursor

@pytest.fixture
def client(mock_db_connection):
    """
    Test client fixture that ensures the DB is mocked.
    """
    return TestClient(app)
