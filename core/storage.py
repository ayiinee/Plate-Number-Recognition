import csv
import sqlite3
from dataclasses import asdict, is_dataclass
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any


DEFAULT_DATABASE_PATH = Path("outputs") / "detections.db"


class DetectionStorage:
    def __init__(self, db_path: str | Path = DEFAULT_DATABASE_PATH):
        self.db_path = Path(db_path)
        self._memory_connection = None

        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._initialize()

    def _connect(self):
        if str(self.db_path) == ":memory:":
            if self._memory_connection is None:
                self._memory_connection = sqlite3.connect(":memory:")

            return self._memory_connection

        return sqlite3.connect(self.db_path)

    def _initialize(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    camera_id TEXT NOT NULL,
                    camera_name TEXT NOT NULL,
                    plate_text TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    source_type TEXT NOT NULL,
                    snapshot_path TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def insert_detection(self, detection: Any) -> int:
        data = self._normalize_detection(detection)

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO detections (
                    timestamp,
                    camera_id,
                    camera_name,
                    plate_text,
                    confidence,
                    source_type,
                    snapshot_path
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["timestamp"],
                    data["camera_id"],
                    data["camera_name"],
                    data["plate_text"],
                    data["confidence"],
                    data["source_type"],
                    data["snapshot_path"],
                ),
            )
            return int(cursor.lastrowid)

    def get_detections(
        self,
        limit: int = 100,
        min_confidence: float | None = None,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT
                id,
                timestamp,
                camera_id,
                camera_name,
                plate_text,
                confidence,
                source_type,
                snapshot_path,
                created_at
            FROM detections
        """
        params: list[Any] = []

        if min_confidence is not None:
            query += " WHERE confidence >= ?"
            params.append(float(min_confidence))

        query += " ORDER BY timestamp ASC, id ASC LIMIT ?"
        params.append(int(limit))

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

        return [dict(row) for row in rows]

    def get_latest_by_camera(self, camera_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT
                    id,
                    timestamp,
                    camera_id,
                    camera_name,
                    plate_text,
                    confidence,
                    source_type,
                    snapshot_path,
                    created_at
                FROM detections
                WHERE camera_id = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT 1
                """,
                (camera_id,),
            ).fetchone()

        return dict(row) if row else None

    def export_csv(self, min_confidence: float | None = None) -> bytes:
        rows = self.get_detections(limit=1_000_000, min_confidence=min_confidence)
        output = StringIO()
        fieldnames = [
            "id",
            "timestamp",
            "camera_id",
            "camera_name",
            "plate_text",
            "confidence",
            "source_type",
            "snapshot_path",
            "created_at",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue().encode("utf-8")

    def clear_all(self):
        with self._connect() as conn:
            conn.execute("DELETE FROM detections")

    def _normalize_detection(self, detection: Any) -> dict[str, Any]:
        if is_dataclass(detection):
            detection = asdict(detection)

        data = dict(detection)
        timestamp = data.get("timestamp") or data.get("waktu")
        camera_name = data.get("camera_name") or data.get("sumber") or "Unknown"
        plate_text = data.get("plate_text") or data.get("plat_nomor")

        return {
            "timestamp": timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "camera_id": data.get("camera_id") or self._camera_id_from_name(camera_name),
            "camera_name": camera_name,
            "plate_text": plate_text or "",
            "confidence": float(data.get("confidence", 0.0)),
            "source_type": data.get("source_type") or "streamlit",
            "snapshot_path": data.get("snapshot_path"),
        }

    def _camera_id_from_name(self, camera_name: str) -> str:
        value = camera_name.lower().strip()
        value = "".join(char if char.isalnum() else "_" for char in value)
        value = "_".join(part for part in value.split("_") if part)
        return value or "unknown"
