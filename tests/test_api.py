"""Tests for API endpoints."""


def test_symbols_autocomplete(client):
    """Symbol autocomplete returns matching symbols."""
    response = client.get("/api/symbols?q=AA")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_symbols_autocomplete_empty_query(client):
    """Symbol autocomplete with no query returns all symbols."""
    response = client.get("/api/symbols")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_types_endpoint(client):
    """Types endpoint returns all transaction types."""
    response = client.get("/api/types")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
