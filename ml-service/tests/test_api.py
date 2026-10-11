"""Integration and endpoint tests for TicketTriage FastAPI service."""
import pytest
from fastapi.testclient import TestClient
from api.main import app, seed_sample_tickets
from api.db import get_db, SessionLocal, TicketModel, init_db


@pytest.fixture
def client():
    init_db()
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["domain"] == "saas"
    assert data["total_labels"] == 11
    assert data["total_teams"] == 8


def test_config_endpoint(client):
    response = client.get("/config")
    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "saas"
    assert len(data["labels"]) == 11
    assert len(data["teams"]) == 8
    assert len(data["priorities"]) == 4
    priority_ids = [p["id"] for p in data["priorities"]]
    assert "P1" in priority_ids
    assert "P4" in priority_ids


def test_predict_endpoint(client):
    payload = {
        "subject": "Checkout API returns 500 since this morning and we were charged twice",
        "body": "Our production users are receiving 500 Internal Server Error when accessing /v1/checkout/charge. Also duplicate billing occurred.",
        "customer_tier": "enterprise",
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_labels" in data
    assert "label_probabilities" in data
    assert "sla" in data
    sla = data["sla"]
    assert sla["priority"] in ["P1", "P2", "P3", "P4"]
    assert len(sla["teams"]) > 0
    assert "first_response_due" in sla
    assert "resolution_due" in sla


def test_create_and_query_ticket(client):
    payload = {
        "subject": "Platform down: cannot reach dashboard",
        "body": "All requests are failing with 503 Service Unavailable.",
        "customer_tier": "free",
    }
    create_resp = client.post("/tickets", json=payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    ticket_id = created["id"]
    assert ticket_id.startswith("TICK-SAAS-")
    assert created["subject"] == payload["subject"]
    assert created["is_responded"] is False
    assert created["is_resolved"] is False

    # Query single ticket
    get_resp = client.get(f"/tickets/{ticket_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == ticket_id

    # List tickets with filter
    list_resp = client.get("/tickets", params={"tier": "free"})
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert items["total"] >= 1
    assert any(t["id"] == ticket_id for t in items["tickets"])


def test_patch_ticket_and_feedback(client):
    # Create ticket
    create_resp = client.post("/tickets", json={
        "subject": "Need help with API webhook setup",
        "body": "Where do I configure our webhook secret?",
        "customer_tier": "pro",
    })
    ticket_id = create_resp.json()["id"]

    # Patch ticket with corrected labels and agent notes
    patch_resp = client.patch(
        f"/tickets/{ticket_id}",
        json={
            "corrected_labels": ["integration-issue", "how-to-question"],
            "agent_notes": "Clarified as integration guidance",
            "is_responded": True,
        },
    )
    assert patch_resp.status_code == 200
    patched = patch_resp.json()
    assert patched["corrected_labels"] == ["integration-issue", "how-to-question"]
    assert patched["is_responded"] is True
    assert patched["responded_at"] is not None
    assert "Integrations" in patched["assigned_teams"]
    assert "Customer Success" in patched["assigned_teams"]


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "saas"
    assert "sla_metrics" in data
    sla = data["sla_metrics"]
    assert "total_tickets" in sla
    assert "by_priority" in sla
    assert "by_team" in sla
