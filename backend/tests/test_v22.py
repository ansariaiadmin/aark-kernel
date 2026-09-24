import os

os.environ.setdefault("API_SECRET_KEY", "test-secret-key-that-is-long-enough-32chars-for-test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from unittest.mock import AsyncMock, MagicMock, patch

import app.core.config as config_module
from fastapi.testclient import TestClient

config_module.get_settings.cache_clear()

# Mock init_db to avoid real DB init
with patch("app.db.init_db.init_db", new=AsyncMock()), patch(
    "app.db.session.engine", MagicMock()
):
    from app.main import app

client = TestClient(app)


def test_nobitex_security_key_validation():
    response = client.post(
        "/api/v1/nobitex/save-key",
        json={"api_key": "short_key"},
    )

    assert response.status_code == 422


def test_nobitex_status_route():
    response = client.get("/api/v1/nobitex/status")

    assert response.status_code == 200
    assert "connected" in response.json()


def test_risk_evaluation_boundary():
    fake_decision = {
        "action": "BUY",
        "confidence": 80,
        "allocated_irt": 2_000_000,
        "reason": "تحلیل آزمایشی",
        "reply_message": "تصمیم آزمایشی برای تست کنترل ریسک",
    }

    with patch(
        "app.main.brain.evaluate_market",
        new=AsyncMock(return_value=fake_decision),
    ):
        response = client.post(
            "/api/v1/agent/evaluate",
            json={
                "wallet_balance_irt": 10_000_000,
                "market_context": "سناریوی آزمایشی",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert "risk_validation" in data
    assert "execution" in data
    assert data["execution"]["allocated_irt"] <= 2_000_000


def test_risk_rejects_allocation_above_twenty_percent():
    fake_decision = {
        "action": "BUY",
        "confidence": 95,
        "allocated_irt": 5_000_000,
        "reason": "تخصیص بیش از سقف مجاز",
        "reply_message": "این سفارش باید رد شود",
    }

    with patch(
        "app.main.brain.evaluate_market",
        new=AsyncMock(return_value=fake_decision),
    ):
        response = client.post(
            "/api/v1/agent/evaluate",
            json={
                "wallet_balance_irt": 10_000_000,
                "market_context": "خرید آزمایشی",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["risk_validation"]["approved"] is False
    assert data["execution"]["allocated_irt"] == 0

def test_get_registered_agents():
    client = TestClient(app)
    res = client.get("/api/v1/agents")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    agent_ids = [a["id"] for a in data["agents"]]
    assert "core_orchestrator" in agent_ids
    assert "accounting_bridge" in agent_ids

def test_accounting_sync_webhook():
    client = TestClient(app)
    payload = {"event": "invoice_created", "amount": 50000000, "currency": "IRT"}
    res = client.post("/api/v1/integrations/accounting/sync", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "synced"
    assert "journal_entry_id" in data
    assert data["received_payload"] == payload

def test_agent_to_agent_message_delivery():
    client = TestClient(app)
    msg = {
        "sender_id": "accounting_bridge",
        "target_id": "core_orchestrator",
        "action": "QUERY_BALANCE",
        "payload": {"vault": "primary"}
    }
    res = client.post("/api/v1/agents/message", json=msg)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "delivered"
    assert data["ack"]["action"] == "QUERY_BALANCE"
