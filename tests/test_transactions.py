def test_transactions_page_renders(client):
    """Transactions page renders successfully."""
    response = client.get("/transactions")
    assert response.status_code == 200
    assert "Transactions" in response.text


def test_transactions_page_with_filters(client):
    """Transactions page accepts filter parameters."""
    response = client.get("/transactions?symbol=AAPL&type=BUY")
    assert response.status_code == 200


def test_transaction_detail_not_found(client):
    """Non-existent transaction returns 404."""
    response = client.get("/transactions/99999")
    assert response.status_code == 404
