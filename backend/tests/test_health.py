from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "operational"


def test_list_tickets():
    response = client.get("/api/tickets")
    assert response.status_code == 200
    tickets = response.json()
    assert any(t["ticket_id"] == "PH-1042" for t in tickets)
