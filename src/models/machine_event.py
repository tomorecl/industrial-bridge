from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MachineEvent:
    machine_id: str
    event_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "machine_id": self.machine_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
        }
