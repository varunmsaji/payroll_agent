"""
Basic health check and API availability tests.
"""

import pytest
from fastapi import status


def test_app_startup(test_client):
    """
    Test that the FastAPI application starts up successfully.
    """
    # The test_client fixture should successfully create a client
    assert test_client is not None


def test_root_endpoint_exists(test_client):
    """
    Test that we can at least access the application.
    This might return 404 if no root endpoint is defined, but shouldn't error.
    """
    response = test_client.get("/")
    # We expect either 200 (if root exists) or 404 (if not defined)
    # But NOT 500 or other server errors
    assert response.status_code in [200, 404, 405]


def test_docs_endpoint_available(test_client):
    """
    Test that FastAPI's automatic docs are available.
    """
    response = test_client.get("/docs")
    assert response.status_code == status.HTTP_200_OK


def test_openapi_endpoint_available(test_client):
    """
    Test that the OpenAPI schema endpoint is available.
    """
    response = test_client.get("/openapi.json")
    assert response.status_code == status.HTTP_200_OK

    # Verify it's valid JSON
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema


@pytest.mark.integration
def test_api_routes_registered(test_client):
    """
    Test that API routes are properly registered.
    This checks the OpenAPI schema for expected endpoints.
    """
    response = test_client.get("/openapi.json")
    schema = response.json()
    paths = schema.get("paths", {})

    # Check that we have some paths registered
    assert len(paths) > 0, "No API routes registered"

    # Check for expected route prefixes
    path_list = list(paths.keys())

    # We expect to see face recognition routes
    face_routes = [p for p in path_list if "/faces/" in p]
    assert len(face_routes) > 0, "Face recognition routes not found"
