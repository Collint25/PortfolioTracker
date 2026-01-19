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


def test_transactions_page_with_multi_symbol_filter(client):
    """Transactions page accepts multiple symbol parameters."""
    response = client.get("/transactions?symbol=AAPL&symbol=MSFT&symbol_mode=include")
    assert response.status_code == 200


def test_transactions_page_with_exclude_type(client):
    """Transactions page accepts exclude mode for types."""
    response = client.get("/transactions?type=DIVIDEND&type_mode=exclude")
    assert response.status_code == 200
