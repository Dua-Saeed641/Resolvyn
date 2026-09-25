"""GET /api/routing — the fruit-fly-inspired swarm router's decisions exposed
over the real HTTP surface (backend/app/api/routes/routing.py), sourced from
the same AGENT_ASSIGNED event agents/nodes.py::route_agent already writes."""

import uuid

from app.services import ticket_service as tickets


def _new_ticket(customer_id: str, text: str) -> str:
    t = tickets.create(uuid.uuid4().hex, channel="Text", customer_id=customer_id)
    tickets.update(t.ticket_id, body=text, subject=text[:140])
    return t.ticket_id


def test_routing_endpoint_lists_a_swarm_decision(client):
    ticket_id = _new_ticket("CUS-20481", "I was charged twice for the same order ORD-83921 and want a refund.")
    r = client.post(f"/api/tickets/{ticket_id}/process", json={})
    assert r.status_code == 200
    assert r.json()["selected_agent"] == "Billing"

    decisions = client.get("/api/routing").json()
    mine = next((d for d in decisions if d["ticket_id"] == ticket_id), None)
    assert mine is not None
    assert mine["winner"] == "Billing"
    assert mine["ambiguous"] is False
    assert len(mine["candidates"]) == 5
    assert all(0.0 <= c["activation_score"] <= 1.0 for c in mine["candidates"])
