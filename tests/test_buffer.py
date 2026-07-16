import json
from pathlib import Path

import pytest

from src.agent.buffer import LocalBuffer
from src.models.machine_event import MachineEvent
from src.models.machine_snapshot import MachineSnapshot


class FakePublisher:
    def __init__(self, fail_times: int = 0):
        self.fail_times = fail_times
        self.calls = 0
        self.published_snapshots = []
        self.published_events = []

    def publish_snapshot(self, snapshot: MachineSnapshot) -> bool:
        self.calls += 1
        if self.fail_times > 0:
            self.fail_times -= 1
            return False
        self.published_snapshots.append(snapshot)
        return True

    def publish_event(self, event: MachineEvent) -> bool:
        self.calls += 1
        if self.fail_times > 0:
            self.fail_times -= 1
            return False
        self.published_events.append(event)
        return True


def _snapshot() -> MachineSnapshot:
    return MachineSnapshot(machine_id="line-01", accepted=10, total=10)


def _event() -> MachineEvent:
    return MachineEvent(
        machine_id="line-01",
        event_type="stop_started",
        payload={"stop_reason_text": "FALLA_MECANICA"},
    )


def test_replay_pending_after_failed_publish(tmp_path: Path):
    buffer = LocalBuffer(tmp_path)
    publisher = FakePublisher()

    buffer.queue_snapshot(_snapshot())
    buffer.queue_event(_event())

    sent_snapshots, sent_events = buffer.replay_pending(publisher)

    assert sent_snapshots == 1
    assert sent_events == 1
    assert len(publisher.published_snapshots) == 1
    assert len(publisher.published_events) == 1
    assert not buffer.pending_snapshots_path.exists()
    assert not buffer.pending_events_path.exists()


def test_replay_keeps_failed_items(tmp_path: Path):
    buffer = LocalBuffer(tmp_path)
    publisher = FakePublisher(fail_times=2)

    buffer.queue_snapshot(_snapshot())

    sent_first, _ = buffer.replay_pending(publisher)
    assert sent_first == 0
    assert buffer.pending_snapshots_path.exists()

    sent_second, _ = buffer.replay_pending(FakePublisher())
    assert sent_second == 1
