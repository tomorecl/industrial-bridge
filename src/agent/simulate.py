import random
from datetime import datetime

from src.models.machine_snapshot import MachineSnapshot


class SimulatedCollector:
    """Genera datos de prueba sin necesitar PLC (útil para demos)."""

    def __init__(self, config: dict):
        self.machine_id = config["machine"]["id"]
        self._tick = 0
        self._accepted = 120
        self._rejected = 4
        self._running = True
        self._stop_active = False
        self._lot = "DEMO-001"
        self._connected = True

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def collect(self) -> MachineSnapshot:
        self._tick += 1

        if self._tick % 15 == 0:
            self._running = not self._running
            self._stop_active = not self._running

        if self._running:
            self._accepted += random.randint(1, 3)
            if random.random() < 0.35:
                self._rejected += random.randint(1, 2)

        if self._tick % 40 == 0:
            lot_num = int(self._lot.split("-")[1]) + 1
            self._lot = f"DEMO-{lot_num:03d}"

        snapshot = MachineSnapshot(
            machine_id=self.machine_id,
            timestamp=datetime.now(),
            plc_connected=self._connected,
            running=self._running,
            accepted=self._accepted,
            rejected=self._rejected,
            total=self._accepted + self._rejected,
            lot=self._lot,
            product="PRODUCTO DEMO",
            operator="OPERADOR DEMO",
            stop_active=self._stop_active,
            stop_reason_code=140 if self._stop_active else None,
            stop_reason_text="FALLA_MECANICA" if self._stop_active else None,
            lot_finished=self._tick % 80 == 0,
        )
        return snapshot
