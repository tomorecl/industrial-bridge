from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MachineSnapshot:
    machine_id: str

    timestamp: datetime = field(default_factory=datetime.now)

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

    def to_dict(self):
        return {
            "machine_id": self.machine_id,
            "timestamp": self.timestamp.isoformat(),
            "plc_connected": self.plc_connected,
            "running": self.running,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "total": self.total,
            "lot": self.lot,
            "product": self.product,
            "operator": self.operator,
            "stop_active": self.stop_active,
            "stop_reason_code": self.stop_reason_code,
            "stop_reason_text": self.stop_reason_text,
            "lot_finished": self.lot_finished,
        }
