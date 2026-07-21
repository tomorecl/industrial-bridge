import logging

import httpx

from src.models.machine_snapshot import MachineSnapshot

logger = logging.getLogger(__name__)


class OpenMesGateway:
    """Publica lecturas normalizadas hacia OpenMES (Machine Gateway API)."""

    def __init__(
        self,
        base_url: str,
        connection_id: int,
        api_token: str,
        tag_map: dict[str, str] | None = None,
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.connection_id = connection_id
        self.timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
        }
        self.tag_map = tag_map or {}

    def _connection_path(self, suffix: str) -> str:
        return (
            f"{self.base_url}/api/v1/machine-connections/"
            f"{self.connection_id}{suffix}"
        )

    def fetch_gateway_config(self) -> dict | None:
        url = self._connection_path("/gateway-config")
        try:
            response = httpx.get(url, headers=self._headers, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as error:
            logger.warning("No se pudo obtener gateway-config de OpenMES: %s", error)
            return None

    def heartbeat(self) -> bool:
        url = self._connection_path("/heartbeat")
        try:
            response = httpx.post(url, headers=self._headers, timeout=self.timeout)
            response.raise_for_status()
            return True
        except Exception as error:
            logger.warning("Heartbeat OpenMES falló: %s", error)
            return False

    def publish_snapshot(self, snapshot: MachineSnapshot) -> bool:
        readings = self.snapshot_to_readings(snapshot)
        if not readings:
            return False
        return self.publish_readings(readings)

    def publish_readings(self, readings: list[dict]) -> bool:
        url = self._connection_path("/signals")
        try:
            response = httpx.post(
                url,
                headers=self._headers,
                json={"readings": readings},
                timeout=self.timeout,
            )
            response.raise_for_status()
            accepted = response.json().get("accepted", 0)
            if accepted < len(readings):
                logger.warning(
                    "OpenMES aceptó %d/%d lecturas (revisa tags/node_id)",
                    accepted,
                    len(readings),
                )
            return accepted > 0
        except Exception as error:
            logger.warning("No se pudo publicar señales en OpenMES: %s", error)
            return False

    def snapshot_to_readings(self, snapshot: MachineSnapshot) -> list[dict]:
        """Mapea campos del snapshot a node_id definidos en OpenMES MachineTags."""
        ts = snapshot.timestamp.isoformat()
        field_values: dict[str, object] = {
            "running": 1 if snapshot.running else 0,
            "accepted": snapshot.accepted,
            "rejected": snapshot.rejected,
            "total": snapshot.total,
            "stop_active": snapshot.stop_active,
            "lot_finished": snapshot.lot_finished,
            "plc_connected": snapshot.plc_connected,
        }
        if snapshot.stop_reason_code is not None:
            field_values["stop_reason_code"] = snapshot.stop_reason_code

        readings: list[dict] = []
        for field, node_id in self.tag_map.items():
            if field not in field_values:
                continue
            readings.append(
                {
                    "node_id": node_id,
                    "value": field_values[field],
                    "ts": ts,
                }
            )
        return readings
