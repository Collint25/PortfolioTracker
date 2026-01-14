def test_health_check(client):
    """Health endpoint returns ok status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_page(client):
    """Index page renders successfully."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Portfolio Tracker" in response.text
