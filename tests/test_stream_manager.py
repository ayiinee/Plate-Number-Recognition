from core.stream_manager import StreamManager
from core.stream_worker import StreamWorkerStatus


class FakeWorker:
    def __init__(self, camera_id):
        self.camera_id = camera_id
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def get_status(self):
        return StreamWorkerStatus(
            camera_id=self.camera_id,
            camera_name=self.camera_id,
            running=self.started and not self.stopped,
            connected=self.started and not self.stopped,
            frame_count=0,
            processed_frame_count=0,
        )

    def get_latest_frame(self):
        return f"frame-{self.camera_id}"


def make_config():
    return {
        "processing": {
            "frame_skip": 2,
            "min_confidence": 0.5,
            "cooldown_seconds": 5,
        },
        "storage": {
            "database_path": ":memory:",
            "snapshot_dir": ".tmp/test_snapshots",
        },
        "sources": {
            "cam_1": {
                "name": "Kamera 1",
                "mode": "demo",
                "live_url": "rtsp://cam-1",
                "demo_path": "data/cam_1.mp4",
            },
            "cam_2": {
                "name": "Kamera 2",
                "mode": "demo",
                "live_url": "rtsp://cam-2",
                "demo_path": "data/cam_2.mp4",
            },
        },
    }


def test_stream_manager_starts_all_workers():
    created = {}

    def worker_factory(camera_id):
        created[camera_id] = FakeWorker(camera_id)
        return created[camera_id]

    manager = StreamManager(
        config=make_config(),
        alpr_factory=lambda: None,
        worker_factory=worker_factory,
    )

    manager.start_all()
    statuses = manager.get_status()

    assert set(created) == {"cam_1", "cam_2"}
    assert statuses["cam_1"].running
    assert statuses["cam_2"].running


def test_stream_manager_restarts_worker_when_mode_changes():
    created = []

    def worker_factory(camera_id):
        worker = FakeWorker(camera_id)
        created.append(worker)
        return worker

    manager = StreamManager(
        config=make_config(),
        alpr_factory=lambda: None,
        worker_factory=worker_factory,
    )

    manager.start_worker("cam_1")
    first_worker = created[0]
    manager.set_mode("cam_1", "live")
    second_worker = created[1]
    resolved = manager.resolver.resolve("cam_1")

    assert first_worker.stopped
    assert second_worker.started
    assert resolved.source == "rtsp://cam-1"


def test_stream_manager_returns_latest_frame():
    manager = StreamManager(
        config=make_config(),
        alpr_factory=lambda: None,
        worker_factory=lambda camera_id: FakeWorker(camera_id),
    )

    manager.start_worker("cam_1")

    assert manager.get_latest_frame("cam_1") == "frame-cam_1"
    assert manager.get_latest_frame("cam_missing") is None
