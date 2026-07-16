from pathlib import Path

from fastapi.testclient import TestClient

from src.server.main import app
from src.server.store import SnapshotStore


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_store_snapshot_and_event(tmp_path: Path):
    store = SnapshotStore(tmp_path / "test.db")
    snapshot = {
        "machine_id": "line-01",
        "timestamp": "2026-07-15T12:00:00",
        "running": True,
        "total": 100,
    }
    event = {
        "machine_id": "line-01",
        "event_type": "stop_started",
        "timestamp": "2026-07-15T12:01:00",
        "payload": {"stop_reason_text": "FALLA_MECANICA"},
    }

    store.save_snapshot(snapshot)
    store.save_event(event)

    assert store.latest_snapshot("line-01")["total"] == 100
    assert store.list_events("line-01")[0]["event_type"] == "stop_started"
    assert store.list_machines() == ["line-01"]
