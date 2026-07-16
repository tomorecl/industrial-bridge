from src.agent.events import EventDetector
from src.models.machine_snapshot import MachineSnapshot


def _snapshot(**kwargs) -> MachineSnapshot:
    data = {
        "machine_id": "line-01",
        "plc_connected": True,
        "running": True,
        "accepted": 10,
        "rejected": 1,
        "total": 11,
        "lot": "L001",
        "product": "PROD",
        "operator": "OP1",
        "stop_active": False,
        "stop_reason_code": None,
        "stop_reason_text": None,
        "lot_finished": False,
    }
    data.update(kwargs)
    return MachineSnapshot(**data)


def test_first_snapshot_emits_no_events():
    detector = EventDetector()
    events = detector.detect(_snapshot())
    assert events == []


def test_detects_stop_started_and_ended():
    detector = EventDetector()
    detector.detect(_snapshot(stop_active=False))

    started = detector.detect(
        _snapshot(
            stop_active=True,
            stop_reason_code=140,
            stop_reason_text="FALLA_MECANICA",
            running=False,
        )
    )
    assert any(event.event_type == "stop_started" for event in started)
    assert any(event.event_type == "running_changed" for event in started)

    ended = detector.detect(_snapshot(stop_active=False, running=True))
    assert any(event.event_type == "stop_ended" for event in ended)
    stop_ended = next(event for event in ended if event.event_type == "stop_ended")
    assert stop_ended.payload["stop_reason_text"] == "FALLA_MECANICA"


def test_detects_lot_changed_and_finished():
    detector = EventDetector()
    detector.detect(_snapshot(lot="L001", lot_finished=False))

    changed = detector.detect(_snapshot(lot="L002", lot_finished=False))
    assert any(event.event_type == "lot_changed" for event in changed)

    finished = detector.detect(_snapshot(lot="L002", lot_finished=True))
    assert any(event.event_type == "lot_finished" for event in finished)
