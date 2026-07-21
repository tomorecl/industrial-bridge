import argparse
import json
import logging
import signal
import time
from pathlib import Path

from src.agent.buffer import LocalBuffer
from src.agent.collector import SnapshotCollector
from src.agent.events import EventDetector
from src.agent.simulate import SimulatedCollector
from src.connectors.http_publisher import HttpPublisher
from src.connectors.openmes_gateway import OpenMesGateway
from src.utils.config_loader import load_machine_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("agent")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "machines" / "example-line.yaml"


class AgentRunner:
    def __init__(self, config: dict, buffer_dir: Path, simulate: bool = False):
        self.config = config
        self.agent_cfg = config.get("agent", {})
        self.poll_interval = float(self.agent_cfg.get("poll_interval_seconds", 1.0))
        self.collector = (
            SimulatedCollector(config) if simulate else SnapshotCollector(config)
        )
        self.simulate = simulate
        self.detector = EventDetector()
        self.buffer = LocalBuffer(buffer_dir)
        self.publisher = None
        server_url = self.agent_cfg.get("server_url")
        if server_url:
            self.publisher = HttpPublisher(server_url)
        self.openmes = self._build_openmes_gateway(config.get("openmes"))
        self._running = True

    def _build_openmes_gateway(self, cfg: dict | None) -> OpenMesGateway | None:
        if not cfg:
            return None
        base_url = cfg.get("base_url")
        connection_id = cfg.get("connection_id")
        api_token = cfg.get("api_token")
        if not base_url or connection_id is None or not api_token:
            return None
        return OpenMesGateway(
            base_url=base_url,
            connection_id=int(connection_id),
            api_token=api_token,
            tag_map=cfg.get("tag_map"),
        )

    def stop(self, *_args) -> None:
        logger.info("Deteniendo agente...")
        self._running = False

    def _replay_pending(self) -> None:
        if not self.publisher:
            return

        sent_snapshots, sent_events = self.buffer.replay_pending(self.publisher)
        if sent_snapshots or sent_events:
            logger.info(
                "Buffer reenviado: %d snapshots, %d eventos",
                sent_snapshots,
                sent_events,
            )

    def _persist(self, snapshot, events) -> None:
        self.buffer.append_snapshot(snapshot)
        self.buffer.append_events(events)

        if self.publisher:
            snapshot_ok = self.publisher.publish_snapshot(snapshot)
            if not snapshot_ok:
                self.buffer.queue_snapshot(snapshot)

            for event in events:
                if not self.publisher.publish_event(event):
                    self.buffer.queue_event(event)

        if self.openmes and not self.openmes.publish_snapshot(snapshot):
            logger.warning("OpenMES no aceptó el snapshot (revisa tags/token)")

    def run_once(self) -> None:
        self._replay_pending()
        snapshot = self.collector.collect()
        events = self.detector.detect(snapshot)
        self._persist(snapshot, events)

        mode = "SIMULACIÓN" if self.simulate else "PLC"
        if snapshot.plc_connected:
            logger.info(
                "[%s] snapshot machine=%s running=%s lot=%s total=%s",
                mode,
                snapshot.machine_id,
                snapshot.running,
                snapshot.lot or "-",
                snapshot.total,
            )
        else:
            logger.warning("PLC desconectado (%s)", snapshot.machine_id)

        for event in events:
            logger.info("event %s %s", event.event_type, event.payload)
            print(json.dumps(event.to_dict(), ensure_ascii=False))

        print(json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False))

    def run_loop(self) -> None:
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        machine_id = self.config["machine"]["id"]
        mode = "SIMULACIÓN" if self.simulate else "PLC"
        logger.info(
            "Iniciando agente [%s] machine=%s poll=%.1fs buffer=%s publisher=%s openmes=%s",
            mode,
            machine_id,
            self.poll_interval,
            self.buffer.directory,
            bool(self.publisher),
            bool(self.openmes),
        )

        if not self.collector.connect():
            logger.error("No se pudo conectar al PLC en el arranque")
        else:
            logger.info("Conexión lista")

        while self._running:
            started = time.monotonic()
            try:
                self._replay_pending()
                snapshot = self.collector.collect()

                if not self.simulate and not snapshot.plc_connected:
                    logger.warning("Reintentando conexión PLC...")
                    self.collector.connect()
                    snapshot = self.collector.collect()

                events = self.detector.detect(snapshot)
                self._persist(snapshot, events)

                if snapshot.plc_connected:
                    logger.info(
                        "[%s] machine=%s running=%s lot=%s total=%s stop=%s events=%d",
                        mode,
                        snapshot.machine_id,
                        snapshot.running,
                        snapshot.lot or "-",
                        snapshot.total,
                        snapshot.stop_active,
                        len(events),
                    )
                else:
                    logger.warning("PLC sin respuesta")

                for event in events:
                    logger.info("event %s %s", event.event_type, event.payload)

            except Exception:
                logger.exception("Error en ciclo de lectura")
                if not self.simulate:
                    self.collector.disconnect()

            elapsed = time.monotonic() - started
            sleep_for = max(0.0, self.poll_interval - elapsed)
            if self._running and sleep_for > 0:
                time.sleep(sleep_for)

        self.collector.disconnect()
        logger.info("Agente detenido")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Raspberry Agent — Industrial Bridge",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Ruta al YAML de la máquina",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Leer una sola vez y salir (útil para pruebas)",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Usar datos simulados sin PLC (demo)",
    )
    parser.add_argument(
        "--buffer-dir",
        type=Path,
        default=PROJECT_ROOT / "logs" / "buffer",
        help="Directorio para snapshots/eventos JSONL",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_machine_config(args.config)
    runner = AgentRunner(config, args.buffer_dir, simulate=args.simulate)

    if args.once:
        if not runner.collector.connect():
            print("❌ No se pudo conectar")
        else:
            label = "✅ Modo simulación" if args.simulate else "✅ PLC conectado"
            print(label)
        try:
            runner.run_once()
        finally:
            runner.collector.disconnect()
        return

    runner.run_loop()


if __name__ == "__main__":
    main()
