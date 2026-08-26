"""
watchlist.py - Watchlist database for face recognition (IBVAP Phase 4).

Stores face embeddings + metadata in SQLite so they persist across restarts.
Provides add/list/delete operations used by the watchlist REST router.

Schema
------
CREATE TABLE watchlist (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    added_at    TEXT NOT NULL,
    image_path  TEXT,
    embedding   BLOB NOT NULL   -- 512 float32 values, numpy tobytes()
)
"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class WatchlistDB:
    """Thread-safe SQLite store for watchlist face embeddings.

    Parameters
    ----------
    db_path : Path
        Path to the SQLite file (can be same DB as events or separate).
    image_dir : Path
        Directory where uploaded face images are saved.
    """

    def __init__(self, db_path: Path, image_dir: Path) -> None:
        import sqlite3
        self._db_path = db_path
        self._image_dir = image_dir
        self._image_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._create_table()
        logger.info("WatchlistDB ready: %s (%d entries)", db_path, self.count())

    def _create_table(self) -> None:
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id          TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    added_at    TEXT NOT NULL,
                    image_path  TEXT,
                    embedding   BLOB NOT NULL
                )
            """)
            self._conn.commit()

    def add(
        self,
        name: str,
        embedding: np.ndarray,
        image_bytes: Optional[bytes] = None,
        image_ext: str = ".jpg",
    ) -> str:
        """Add a person to the watchlist. Returns the new entry ID."""
        entry_id = str(uuid.uuid4())[:8]
        added_at = datetime.now(timezone.utc).isoformat()
        image_path = None

        if image_bytes:
            img_file = self._image_dir / f"{entry_id}{image_ext}"
            img_file.write_bytes(image_bytes)
            image_path = str(img_file)

        emb_blob = embedding.astype(np.float32).tobytes()

        with self._lock:
            self._conn.execute(
                "INSERT INTO watchlist (id, name, added_at, image_path, embedding) "
                "VALUES (?, ?, ?, ?, ?)",
                (entry_id, name, added_at, image_path, emb_blob),
            )
            self._conn.commit()

        logger.info("Watchlist: added '%s' (id=%s)", name, entry_id)
        return entry_id

    def all_entries(self) -> list[dict]:
        """Return all watchlist entries with embeddings as numpy arrays."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, name, added_at, image_path, embedding FROM watchlist"
            ).fetchall()
        entries = []
        for row in rows:
            emb = np.frombuffer(row[4], dtype=np.float32).copy()
            entries.append({
                "id": row[0], "name": row[1],
                "added_at": row[2], "image_path": row[3],
                "embedding": emb,
            })
        return entries

    def list_metadata(self) -> list[dict]:
        """Return all entries WITHOUT embeddings (for the API response)."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, name, added_at, image_path FROM watchlist ORDER BY added_at DESC"
            ).fetchall()
        return [
            {"id": r[0], "name": r[1], "added_at": r[2], "has_image": r[3] is not None}
            for r in rows
        ]

    def delete(self, entry_id: str) -> bool:
        """Delete a watchlist entry. Returns True if found and deleted."""
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM watchlist WHERE id = ?", (entry_id,)
            )
            self._conn.commit()
        deleted = cur.rowcount > 0
        if deleted:
            logger.info("Watchlist: deleted id=%s", entry_id)
        return deleted

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
