import json
from datetime import datetime
from pathlib import Path

from src.models.machine_event import MachineEvent
from src.models.machine_snapshot import MachineSnapshot


class LocalBuffer:
    """Guarda snapshots y eventos en JSONL local (cola offline)."""

    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.snapshots_path = self.directory / "snapshots.jsonl"
        self.events_path = self.directory / "events.jsonl"
        self.pending_snapshots_path = self.directory / "pending_snapshots.jsonl"
        self.pending_events_path = self.directory / "pending_events.jsonl"

    def append_snapshot(self, snapshot: MachineSnapshot) -> None:
        self._append(self.snapshots_path, snapshot.to_dict())

    def append_event(self, event: MachineEvent) -> None:
        self._append(self.events_path, event.to_dict())

    def append_events(self, events: list[MachineEvent]) -> None:
        for event in events:
            self.append_event(event)

    def queue_snapshot(self, snapshot: MachineSnapshot) -> None:
        self._append(self.pending_snapshots_path, snapshot.to_dict())

    def queue_event(self, event: MachineEvent) -> None:
        self._append(self.pending_events_path, event.to_dict())

    def queue_events(self, events: list[MachineEvent]) -> None:
        for event in events:
            self.queue_event(event)

    def replay_pending(self, publisher) -> tuple[int, int]:
        sent_snapshots = self._replay_file(
            self.pending_snapshots_path,
            publisher.publish_snapshot,
            MachineSnapshot,
        )
        sent_events = self._replay_file(
            self.pending_events_path,
            publisher.publish_event,
            MachineEvent,
        )
        return sent_snapshots, sent_events

    def _replay_file(self, path: Path, publish_fn, model_cls) -> int:
        if not path.exists():
            return 0

        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines:
            return 0

        remaining = []
        sent = 0

        for line in lines:
            if not line.strip():
                continue
            data = json.loads(line)
            item = self._build_model(model_cls, data)
            if publish_fn(item):
                sent += 1
            else:
                remaining.append(line)

        if remaining:
            path.write_text("\n".join(remaining) + "\n", encoding="utf-8")
        else:
            path.unlink(missing_ok=True)

        return sent

    def _build_model(self, model_cls, data: dict):
        if model_cls is MachineSnapshot:
            timestamp = data.get("timestamp")
            if isinstance(timestamp, str):
                data = {**data, "timestamp": datetime.fromisoformat(timestamp)}
            return MachineSnapshot(**data)

        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            data = {**data, "timestamp": datetime.fromisoformat(timestamp)}
        return MachineEvent(**data)

    def _append(self, path: Path, payload: dict) -> None:
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False) + "\n")
