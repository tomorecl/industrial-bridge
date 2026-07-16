import logging

from pymodbus.client.sync import ModbusTcpClient

logger = logging.getLogger(__name__)


class ModbusDriver:

    def __init__(self, ip, port=502, slave=1, timeout=3):
        self.ip = ip
        self.port = port
        self.slave = slave
        self.timeout = timeout
        self.client = None

    def connect(self):
        try:
            self.client = ModbusTcpClient(
                self.ip,
                port=self.port,
                timeout=self.timeout,
            )
            connected = self.client.connect()

            if connected:
                logger.info("Conectado a %s:%s", self.ip, self.port)
            else:
                logger.error("No fue posible conectar a %s:%s", self.ip, self.port)

            return connected

        except Exception as error:
            logger.exception("Error Modbus: %s", error)
            return False

    def disconnect(self):
        if self.client:
            self.client.close()
            self.client = None

    def read_holding_register(self, address):
        registers = self.read_holding_registers(address, 1)
        if registers is None:
            return None
        return registers[0]

    def read_holding_registers(self, address, count):
        if not self.client:
            return None

        try:
            response = self.client.read_holding_registers(
                address=address,
                count=count,
                unit=self.slave,
            )
            if response and not response.isError():
                return response.registers
        except Exception as error:
            logger.exception("Error leyendo holding registers %s: %s", address, error)

        return None

    def read_coil(self, address):
        coils = self.read_coils(address, 1)
        if coils is None:
            return None
        return coils[0]

    def read_coils(self, address, count):
        if not self.client:
            return None

        try:
            response = self.client.read_coils(
                address=address,
                count=count,
                unit=self.slave,
            )
            if response and not response.isError() and hasattr(response, "bits"):
                return [bool(bit) for bit in response.bits[:count]]
        except Exception as error:
            logger.exception("Error leyendo coils %s: %s", address, error)

        return None

    def read_fatek_string(self, address, register_count):
        registers = self.read_holding_registers(address, register_count)
        if registers is None:
            return ""

        chars = []
        for register in registers:
            low = register & 0xFF
            high = (register >> 8) & 0xFF

            if low != 0:
                chars.append(chr(low))
            if high != 0:
                chars.append(chr(high))

        return "".join(chars).strip()

    def read_stop_motives(self, m_base, motive_start, motive_count):
        coils = self.read_coils(m_base + motive_start, motive_count)
        if coils is None:
            return None

        return {
            motive_start + index: coils[index]
            for index in range(motive_count)
        }

    def read_active_stop_reason(self, motives, labels):
        if not motives:
            return None, None

        for code, active in sorted(motives.items()):
            if active:
                return code, labels.get(code, "SIN_CLASIFICAR")

        return None, None
