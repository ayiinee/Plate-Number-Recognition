from typing import Callable

from core.config import load_config
from core.event_processor import EventProcessor
from core.source_reader import SourceReader
from core.source_resolver import SourceResolver
from core.storage import DetectionStorage
from core.stream_worker import StreamWorker, StreamWorkerStatus


class StreamManager:
    def __init__(
        self,
        config: dict | None = None,
        alpr_factory: Callable | None = None,
        storage: DetectionStorage | None = None,
        event_processor: EventProcessor | None = None,
        worker_factory: Callable | None = None,
    ):
        self.config = config or load_config()
        self.resolver = SourceResolver(self.config)
        self.processing_config = self.config.get("processing", {})
        self.storage_config = self.config.get("storage", {})
        self.storage = storage or DetectionStorage(
            self.storage_config.get("database_path", "outputs/detections.db")
        )
        self.event_processor = event_processor or EventProcessor(
            storage=self.storage,
            min_confidence=self.processing_config.get("min_confidence", 0.7),
            cooldown_seconds=self.processing_config.get("cooldown_seconds", 5),
            snapshot_dir=self.storage_config.get("snapshot_dir", "outputs/snapshots"),
        )
        self.alpr_factory = alpr_factory or _default_alpr_factory
        self.worker_factory = worker_factory or self._create_worker
        self.workers: dict[str, StreamWorker] = {}

    def start_all(self):
        for camera_id in self.config.get("sources", {}):
            self.start_worker(camera_id)

    def stop_all(self):
        for worker in list(self.workers.values()):
            worker.stop()

    def start_worker(self, camera_id: str):
        worker = self.workers.get(camera_id)

        if worker is None:
            worker = self.worker_factory(camera_id)
            self.workers[camera_id] = worker

        worker.start()

    def stop_worker(self, camera_id: str):
        worker = self.workers.get(camera_id)

        if worker is not None:
            worker.stop()

    def restart_worker(self, camera_id: str):
        self.stop_worker(camera_id)
        self.workers.pop(camera_id, None)
        self.start_worker(camera_id)

    def set_mode(self, camera_id: str, mode: str):
        self.resolver.set_mode(camera_id, mode)

        if camera_id in self.workers:
            self.restart_worker(camera_id)

    def get_status(self) -> dict[str, StreamWorkerStatus]:
        return {
            camera_id: worker.get_status()
            for camera_id, worker in self.workers.items()
        }

    def get_latest_frame(self, camera_id: str):
        worker = self.workers.get(camera_id)

        if worker is None:
            return None

        return worker.get_latest_frame()

    def _create_worker(self, camera_id: str) -> StreamWorker:
        resolved_source = self.resolver.resolve(camera_id)
        alpr = self.alpr_factory()
        reader = SourceReader(resolved_source)

        return StreamWorker(
            resolved_source=resolved_source,
            alpr=alpr,
            event_processor=self.event_processor,
            frame_skip=self.processing_config.get("frame_skip", 5),
            reader=reader,
        )


def _default_alpr_factory():
    from core.alpr_engine import create_alpr_engine

    return create_alpr_engine()
