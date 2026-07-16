from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.server.store import SnapshotStore

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = PROJECT_ROOT / "data" / "industrial_bridge.db"
DASHBOARD_HTML = Path(__file__).resolve().parent / "dashboard.html"

app = FastAPI(
    title="Industrial Bridge — Servidor Central",
    description="Recibe snapshots y eventos desde los Raspberry Agents",
    version="0.2.0",
)
store = SnapshotStore(DEFAULT_DB)


class SnapshotIn(BaseModel):
    machine_id: str
    timestamp: str
    plc_connected: bool = False
    running: bool = False
    accepted: int = 0
    rejected: int = 0
    total: int = 0
    lot: str = ""
    product: str = ""
    operator: str = ""
    stop_active: bool = False
    stop_reason_code: int | None = None
    stop_reason_text: str | None = None
    lot_finished: bool = False


class EventIn(BaseModel):
    machine_id: str
    event_type: str
    timestamp: str
    payload: dict = Field(default_factory=dict)


@app.get("/")
def dashboard():
    return FileResponse(DASHBOARD_HTML)


@app.get("/health")
def health():
    return {"status": "ok", "service": "industrial-bridge-server"}


@app.post("/api/v1/snapshots")
def create_snapshot(snapshot: SnapshotIn):
    row_id = store.save_snapshot(snapshot.model_dump())
    return {"id": row_id, "status": "stored"}


@app.post("/api/v1/events")
def create_event(event: EventIn):
    row_id = store.save_event(event.model_dump())
    return {"id": row_id, "status": "stored"}


@app.get("/api/v1/machines")
def machines():
    return {"machines": store.list_machines()}


@app.get("/api/v1/machines/{machine_id}/latest")
def machine_latest(machine_id: str):
    latest = store.latest_snapshot(machine_id)
    if latest is None:
        raise HTTPException(status_code=404, detail="No hay snapshots para esta máquina")
    return latest


@app.get("/api/v1/machines/{machine_id}/events")
def machine_events(machine_id: str, limit: int = 50):
    return {"machine_id": machine_id, "events": store.list_events(machine_id, limit)}
