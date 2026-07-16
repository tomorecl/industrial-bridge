from src.drivers.modbus import ModbusDriver
from src.models.machine_snapshot import MachineSnapshot


class SnapshotCollector:
    """Lee el PLC usando una conexión Modbus reutilizable."""

    def __init__(self, config: dict):
        self.config = config
        self.machine = config["machine"]
        self.plc = config["plc"]
        self.registers = config["registers"]
        self.coils = config["coils"]
        self.strings = config["strings"]
        self.stop_motives = config["stop_motives"]
        self.driver = ModbusDriver(
            ip=self.plc["ip"],
            port=self.plc.get("port", 502),
            slave=self.plc.get("slave", 1),
            timeout=self.plc.get("timeout", 3),
        )

    def connect(self) -> bool:
        return self.driver.connect()

    def disconnect(self) -> None:
        self.driver.disconnect()

    def collect(self) -> MachineSnapshot:
        snapshot = MachineSnapshot(machine_id=self.machine["id"])

        if self.driver.client is None and not self.connect():
            return snapshot

        snapshot.plc_connected = True

        try:
            snapshot.accepted = (
                self.driver.read_holding_register(self.registers["accepted"]) or 0
            )
            snapshot.rejected = (
                self.driver.read_holding_register(self.registers["rejected"]) or 0
            )
            snapshot.total = (
                self.driver.read_holding_register(self.registers["total"]) or 0
            )

            snapshot.lot = self.driver.read_fatek_string(
                self.strings["lot"]["register"],
                self.strings["lot"]["length"],
            )
            snapshot.product = self.driver.read_fatek_string(
                self.strings["product"]["register"],
                self.strings["product"]["length"],
            )
            snapshot.operator = self.driver.read_fatek_string(
                self.strings["operator"]["register"],
                self.strings["operator"]["length"],
            )

            running_status = self.driver.read_coil(self.coils["running_status"])
            if running_status is not None:
                # En el OEE: X9 activo = DETENIDA
                snapshot.running = not running_status

            snapshot.stop_active = bool(
                self.driver.read_coil(self.plc["m_base"] + self.coils["stop_active"])
            )
            snapshot.lot_finished = bool(
                self.driver.read_coil(self.plc["m_base"] + self.coils["lot_finished"])
            )

            motives = self.driver.read_stop_motives(
                self.plc["m_base"],
                self.stop_motives["start"],
                self.stop_motives["count"],
            )
            reason_code, reason_text = self.driver.read_active_stop_reason(
                motives,
                self.stop_motives.get("labels", {}),
            )
            snapshot.stop_reason_code = reason_code
            snapshot.stop_reason_text = reason_text

        except Exception:
            snapshot.plc_connected = False
            self.disconnect()
            raise

        return snapshot


def collect_snapshot(config: dict) -> MachineSnapshot:
    """Compatibilidad: una sola lectura con connect/disconnect."""
    collector = SnapshotCollector(config)
    try:
        if not collector.connect():
            return MachineSnapshot(machine_id=config["machine"]["id"])
        return collector.collect()
    finally:
        collector.disconnect()
