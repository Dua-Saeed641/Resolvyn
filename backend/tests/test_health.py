def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "operational"
    assert body["llm_ready"] is False  # tests run with no model on purpose


def test_seeded_history_and_knowledge(client):
    tickets = client.get("/api/tickets").json()
    assert any(t["ticket_id"] == "PH-0911" for t in tickets)
    docs = client.get("/api/knowledge").json()
    assert len(docs) >= 7
    stats = client.get("/api/knowledge/stats").json()
    assert stats["chunks"] > 30 and stats["graph"]["nodes"] > 50


def test_system_status(client):
    s = client.get("/api/system").json()
    assert s["agent"] == "Riya"
    assert s["llm"]["live_ready"] is False
