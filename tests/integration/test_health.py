"""Test that FastAPI starts and /health returns 200 with expected payload."""

from fastapi.testclient import TestClient

from backend.main import app


def test_health_ok():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload == {"status": "ok"}
