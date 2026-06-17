import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2

from core.plate_parser import is_valid_indonesian_plate, normalize_plate
from core.storage import DetectionStorage


DEFAULT_SNAPSHOT_DIR = Path("outputs") / "snapshots"


@dataclass
class DetectionEvent:
    timestamp: str
    camera_id: str
    camera_name: str
    plate_text: str
    confidence: float
    source_type: str
    snapshot_path: str | None = None


class EventProcessor:
    def __init__(
        self,
        storage: DetectionStorage,
        min_confidence: float = 0.5,
        cooldown_seconds: int = 5,
        snapshot_dir: str | Path = DEFAULT_SNAPSHOT_DIR,
        save_snapshots: bool = True,
    ):
        self.storage = storage
        self.min_confidence = float(min_confidence)
        self.cooldown_seconds = int(cooldown_seconds)
        self.snapshot_dir = Path(snapshot_dir)
        self.save_snapshots = save_snapshots
        self.last_seen: dict[tuple[str, str], float] = {}

        if self.save_snapshots:
            self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def process_detections(
        self,
        detections: list[dict[str, Any]],
        camera_id: str,
        camera_name: str,
        source_type: str,
        frame=None,
    ) -> list[DetectionEvent]:
        accepted_events = []

        for detection in detections:
            event = self.process_detection(
                detection=detection,
                camera_id=camera_id,
                camera_name=camera_name,
                source_type=source_type,
                frame=frame,
            )

            if event is not None:
                accepted_events.append(event)

        return accepted_events

    def process_detection(
        self,
        detection: dict[str, Any],
        camera_id: str,
        camera_name: str,
        source_type: str,
        frame=None,
    ) -> DetectionEvent | None:
        plate_text = normalize_plate(detection.get("plate") or detection.get("plate_text"))
        confidence = float(detection.get("confidence", 0.0))

        if confidence < self.min_confidence:
            return None

        if not is_valid_indonesian_plate(plate_text):
            return None

        key = (camera_id, plate_text)
        now = time.time()
        last_time = self.last_seen.get(key, 0)

        if now - last_time < self.cooldown_seconds:
            return None

        self.last_seen[key] = now

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        snapshot_path = self._save_snapshot(
            frame=frame,
            camera_id=camera_id,
            plate_text=plate_text,
            timestamp=timestamp,
        )

        event = DetectionEvent(
            timestamp=timestamp,
            camera_id=camera_id,
            camera_name=camera_name,
            plate_text=plate_text,
            confidence=round(confidence, 4),
            source_type=source_type,
            snapshot_path=snapshot_path,
        )

        self.storage.insert_detection(asdict(event))

        return event

    def _save_snapshot(
        self,
        frame,
        camera_id: str,
        plate_text: str,
        timestamp: str,
    ) -> str | None:
        if not self.save_snapshots or frame is None:
            return None

        safe_timestamp = timestamp.replace("-", "").replace(":", "").replace(" ", "_")
        filename = f"{camera_id}_{safe_timestamp}_{plate_text}.jpg"
        path = self.snapshot_dir / filename

        success = cv2.imwrite(str(path), frame)

        if not success:
            return None

        return str(path)
