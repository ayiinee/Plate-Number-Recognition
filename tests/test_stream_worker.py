import numpy as np

from core.event_processor import EventProcessor
from core.source_resolver import ResolvedSource
from core.storage import DetectionStorage
from core.stream_worker import StreamWorker


class FakeReader:
    def __init__(self, frames):
        self.frames = list(frames)
        self.released = False

    def read(self):
        if not self.frames:
            return False, None

        return True, self.frames.pop(0)

    def release(self):
        self.released = True


def fake_predict(alpr, frame):
    return frame + 1, [{"plate": "B1234CD", "confidence": 0.9}]


def fake_extract(results):
    return results


def test_stream_worker_processes_frame_after_frame_skip():
    storage = DetectionStorage(":memory:")
    processor = EventProcessor(
        storage=storage,
        min_confidence=0.5,
        cooldown_seconds=5,
        save_snapshots=False,
    )
    source = ResolvedSource(
        camera_id="cam_1",
        camera_name="Kamera 1",
        mode="demo",
        source="fake.mp4",
        source_type="demo",
    )
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    reader = FakeReader([frame, frame])
    worker = StreamWorker(
        resolved_source=source,
        alpr=None,
        event_processor=processor,
        frame_skip=2,
        reader=reader,
        predict_func=fake_predict,
        extract_func=fake_extract,
        idle_sleep_seconds=0,
    )

    processed = worker.run_once()
    status = worker.get_status()

    assert processed
    assert status.frame_count == 2
    assert status.processed_frame_count == 1
    assert status.last_event is not None
    assert storage.get_latest_by_camera("cam_1")["plate_text"] == "B1234CD"


def test_stream_worker_latest_frame_uses_annotated_frame():
    storage = DetectionStorage(":memory:")
    processor = EventProcessor(storage=storage, save_snapshots=False)
    source = ResolvedSource("cam_1", "Kamera 1", "demo", "fake.mp4", "demo")
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    worker = StreamWorker(
        resolved_source=source,
        alpr=None,
        event_processor=processor,
        frame_skip=1,
        reader=FakeReader([frame]),
        predict_func=fake_predict,
        extract_func=fake_extract,
        idle_sleep_seconds=0,
    )

    worker.run_once()
    latest_frame = worker.get_latest_frame()

    assert latest_frame is not None
    assert int(latest_frame[0, 0, 0]) == 1
