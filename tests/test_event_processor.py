from pathlib import Path

import numpy as np

from core.event_processor import EventProcessor
from core.storage import DetectionStorage


def test_event_processor_accepts_valid_detection():
    storage = DetectionStorage(":memory:")
    processor = EventProcessor(
        storage=storage,
        min_confidence=0.5,
        cooldown_seconds=5,
        save_snapshots=False,
    )

    events = processor.process_detections(
        detections=[{"plate": "B1234CD", "confidence": 0.9}],
        camera_id="cam_1",
        camera_name="Kamera 1",
        source_type="demo",
    )

    assert len(events) == 1
    assert events[0].plate_text == "B1234CD"
    assert storage.get_latest_by_camera("cam_1")["plate_text"] == "B1234CD"


def test_event_processor_rejects_invalid_plate():
    storage = DetectionStorage(":memory:")
    processor = EventProcessor(storage=storage, save_snapshots=False)

    events = processor.process_detections(
        detections=[{"plate": "PLAT123", "confidence": 0.9}],
        camera_id="cam_1",
        camera_name="Kamera 1",
        source_type="demo",
    )

    assert events == []
    assert storage.get_detections() == []


def test_event_processor_rejects_low_confidence():
    storage = DetectionStorage(":memory:")
    processor = EventProcessor(
        storage=storage,
        min_confidence=0.8,
        save_snapshots=False,
    )

    events = processor.process_detections(
        detections=[{"plate": "B1234CD", "confidence": 0.7}],
        camera_id="cam_1",
        camera_name="Kamera 1",
        source_type="demo",
    )

    assert events == []
    assert storage.get_detections() == []


def test_event_processor_deduplicates_by_camera_and_plate():
    storage = DetectionStorage(":memory:")
    processor = EventProcessor(
        storage=storage,
        min_confidence=0.5,
        cooldown_seconds=30,
        save_snapshots=False,
    )

    first_events = processor.process_detections(
        detections=[{"plate": "B1234CD", "confidence": 0.9}],
        camera_id="cam_1",
        camera_name="Kamera 1",
        source_type="demo",
    )
    second_events = processor.process_detections(
        detections=[{"plate": "B1234CD", "confidence": 0.95}],
        camera_id="cam_1",
        camera_name="Kamera 1",
        source_type="demo",
    )

    assert len(first_events) == 1
    assert second_events == []
    assert len(storage.get_detections()) == 1


def test_event_processor_saves_snapshot():
    storage = DetectionStorage(":memory:")
    snapshot_dir = Path(".tmp") / "test_snapshots"
    processor = EventProcessor(
        storage=storage,
        min_confidence=0.5,
        cooldown_seconds=5,
        snapshot_dir=snapshot_dir,
        save_snapshots=True,
    )
    frame = np.zeros((20, 20, 3), dtype=np.uint8)

    events = processor.process_detections(
        detections=[{"plate": "B1234CD", "confidence": 0.9}],
        camera_id="cam_1",
        camera_name="Kamera 1",
        source_type="demo",
        frame=frame,
    )

    assert len(events) == 1
    assert events[0].snapshot_path is not None
    assert Path(events[0].snapshot_path).exists()
