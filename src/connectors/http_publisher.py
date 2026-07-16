import logging

import httpx

from src.models.machine_event import MachineEvent
from src.models.machine_snapshot import MachineSnapshot

logger = logging.getLogger(__name__)


class HttpPublisher:
    """Publica snapshots y eventos hacia el servidor central (API REST)."""

    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def publish_snapshot(self, snapshot: MachineSnapshot) -> bool:
        return self._post("/api/v1/snapshots", snapshot.to_dict())

    def publish_event(self, event: MachineEvent) -> bool:
        return self._post("/api/v1/events", event.to_dict())

    def publish_events(self, events: list[MachineEvent]) -> int:
        ok = 0
        for event in events:
            if self.publish_event(event):
                ok += 1
        return ok

    def _post(self, path: str, payload: dict) -> bool:
        url = f"{self.base_url}{path}"
        try:
            response = httpx.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return True
        except Exception as error:
            logger.warning("No se pudo publicar en %s: %s", url, error)
            return False
