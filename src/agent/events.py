from src.models.machine_event import MachineEvent
from src.models.machine_snapshot import MachineSnapshot


class EventDetector:
    """Detecta cambios por flanco entre dos snapshots consecutivos."""

    def __init__(self):
        self._previous: MachineSnapshot | None = None
        self._last_lot: str | None = None
        self._lot_finished_previous = False
        self._pending_stop_reason_code: int | None = None
        self._pending_stop_reason_text: str | None = None

    def detect(self, snapshot: MachineSnapshot) -> list[MachineEvent]:
        events: list[MachineEvent] = []
        previous = self._previous

        if previous is None:
            self._previous = snapshot
            self._last_lot = snapshot.lot.strip() or None
            self._lot_finished_previous = snapshot.lot_finished
            return events

        if previous.plc_connected != snapshot.plc_connected:
            events.append(
                MachineEvent(
                    machine_id=snapshot.machine_id,
                    event_type=(
                        "plc_connected"
                        if snapshot.plc_connected
                        else "plc_disconnected"
                    ),
                )
            )

        if previous.running != snapshot.running:
            events.append(
                MachineEvent(
                    machine_id=snapshot.machine_id,
                    event_type="running_changed",
                    payload={
                        "running": snapshot.running,
                        "previous_running": previous.running,
                    },
                )
            )

        if snapshot.stop_active and not previous.stop_active:
            self._pending_stop_reason_code = snapshot.stop_reason_code
            self._pending_stop_reason_text = snapshot.stop_reason_text
            events.append(
                MachineEvent(
                    machine_id=snapshot.machine_id,
                    event_type="stop_started",
                    payload={
                        "stop_reason_code": snapshot.stop_reason_code,
                        "stop_reason_text": snapshot.stop_reason_text,
                        "lot": snapshot.lot,
                        "product": snapshot.product,
                        "operator": snapshot.operator,
                    },
                )
            )
        elif snapshot.stop_active and previous.stop_active:
            if (
                snapshot.stop_reason_code is not None
                and self._pending_stop_reason_code is None
            ):
                self._pending_stop_reason_code = snapshot.stop_reason_code
                self._pending_stop_reason_text = snapshot.stop_reason_text
                events.append(
                    MachineEvent(
                        machine_id=snapshot.machine_id,
                        event_type="stop_reason_set",
                        payload={
                            "stop_reason_code": snapshot.stop_reason_code,
                            "stop_reason_text": snapshot.stop_reason_text,
                        },
                    )
                )

        if previous.stop_active and not snapshot.stop_active:
            events.append(
                MachineEvent(
                    machine_id=snapshot.machine_id,
                    event_type="stop_ended",
                    payload={
                        "stop_reason_code": self._pending_stop_reason_code,
                        "stop_reason_text": self._pending_stop_reason_text,
                        "lot": snapshot.lot,
                    },
                )
            )
            self._pending_stop_reason_code = None
            self._pending_stop_reason_text = None

        current_lot = snapshot.lot.strip()
        if current_lot and current_lot != (self._last_lot or ""):
            events.append(
                MachineEvent(
                    machine_id=snapshot.machine_id,
                    event_type="lot_changed",
                    payload={
                        "lot": current_lot,
                        "previous_lot": self._last_lot,
                        "product": snapshot.product,
                        "operator": snapshot.operator,
                    },
                )
            )
            self._last_lot = current_lot

        if snapshot.lot_finished and not self._lot_finished_previous:
            events.append(
                MachineEvent(
                    machine_id=snapshot.machine_id,
                    event_type="lot_finished",
                    payload={
                        "lot": snapshot.lot,
                        "accepted": snapshot.accepted,
                        "rejected": snapshot.rejected,
                        "total": snapshot.total,
                    },
                )
            )

        self._lot_finished_previous = snapshot.lot_finished
        self._previous = snapshot
        return events
