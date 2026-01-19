"""Tests for API endpoints."""


def test_types_endpoint(client):
    """Types endpoint returns all transaction types."""
    response = client.get("/api/types")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
