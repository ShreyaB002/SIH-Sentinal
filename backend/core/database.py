"""
database.py ? SQLite event persistence for IBVAP Phase 2.

Provides a lightweight wrapper around a single SQLite database file.
All writes go through a threading.Lock so the database is safe to use
from multiple camera threads simultaneously.

Schema
------
events
    id          INTEGER PRIMARY KEY AUTOINCREMENT
    timestamp   TEXT    ISO-8601 UTC timestamp
    camera_id   TEXT
    camera_name TEXT
    event_type  TEXT    e.g. "INTRUSION", "PERSON_DETECTED"
    label       TEXT    detected object class
    confidence  REAL    detection confidence (0-1)
    zone        TEXT    zone name (empty string if not zone-triggered)
    track_id    INTEGER tracker-assigned object ID
    bbox_json   TEXT    JSON-encoded [x1,y1,x2,y2]
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class Database:
    """Thread-safe SQLite event store.

    Parameters
    ----------
    db_path:
        Path to the SQLite file. Created if it does not exist.
    """

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        """Create the events table if it does not already exist."""
        db_path = self._path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            conn = self._connect()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT    NOT NULL,
                    camera_id   TEXT    NOT NULL,
                    camera_name TEXT    NOT NULL,
                    event_type  TEXT    NOT NULL,
                    label       TEXT    NOT NULL,
                    confidence  REAL    NOT NULL,
                    zone        TEXT    NOT NULL DEFAULT '',
                    track_id    INTEGER NOT NULL DEFAULT 0,
                    bbox_json   TEXT    NOT NULL DEFAULT '[]'
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_camera ON events(camera_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON events(timestamp)")
            conn.commit()
            conn.close()
        logger.info("Database ready: %s", self._path)

    def insert_event(
        self,
        camera_id: str,
        camera_name: str,
        event_type: str,
        label: str,
        confidence: float,
        zone: str = "",
        track_id: int = 0,
        bbox: tuple[int, int, int, int] = (0, 0, 0, 0),
    ) -> int:
        """Insert one event row and return the new row ID."""
        ts = datetime.now(timezone.utc).isoformat()
        bbox_json = json.dumps(list(bbox))
        with self._lock:
            conn = self._connect()
            cur = conn.execute(
                """
                INSERT INTO events
                    (timestamp, camera_id, camera_name, event_type, label,
                     confidence, zone, track_id, bbox_json)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (ts, camera_id, camera_name, event_type, label,
                 confidence, zone, track_id, bbox_json),
            )
            row_id = cur.lastrowid
            conn.commit()
            conn.close()
        return row_id

    def query_events(
        self,
        camera_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Return recent events as a list of dicts, newest first."""
        query = "SELECT * FROM events"
        params: list = []
        if camera_id:
            query += " WHERE camera_id = ?"
            params.append(camera_id)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            conn = self._connect()
            rows = conn.execute(query, params).fetchall()
            conn.close()

        return [dict(row) for row in rows]
