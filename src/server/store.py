import json
import sqlite3
from pathlib import Path


class SnapshotStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_snapshots_machine
                    ON snapshots(machine_id, timestamp DESC);

                CREATE INDEX IF NOT EXISTS idx_events_machine
                    ON events(machine_id, timestamp DESC);
                """
            )

    def save_snapshot(self, data: dict) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO snapshots (machine_id, timestamp, payload)
                VALUES (?, ?, ?)
                """,
                (
                    data["machine_id"],
                    data["timestamp"],
                    json.dumps(data, ensure_ascii=False),
                ),
            )
            return int(cursor.lastrowid)

    def save_event(self, data: dict) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (machine_id, event_type, timestamp, payload)
                VALUES (?, ?, ?, ?)
                """,
                (
                    data["machine_id"],
                    data["event_type"],
                    data["timestamp"],
                    json.dumps(data, ensure_ascii=False),
                ),
            )
            return int(cursor.lastrowid)

    def latest_snapshot(self, machine_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload
                FROM snapshots
                WHERE machine_id = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT 1
                """,
                (machine_id,),
            ).fetchone()
        if not row:
            return None
        return json.loads(row["payload"])

    def list_events(self, machine_id: str, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload
                FROM events
                WHERE machine_id = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                (machine_id, limit),
            ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def list_machines(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT machine_id
                FROM snapshots
                ORDER BY machine_id
                """
            ).fetchall()
        return [row["machine_id"] for row in rows]
