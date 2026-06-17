import threading
import time
from dataclasses import dataclass
from typing import Callable

from core.event_processor import DetectionEvent, EventProcessor
from core.plate_parser import extract_plate_results
from core.source_reader import SourceReader
from core.source_resolver import ResolvedSource


@dataclass
class StreamWorkerStatus:
    camera_id: str
    camera_name: str
    running: bool
    connected: bool
    frame_count: int
    processed_frame_count: int
    last_error: str | None = None
    last_event: DetectionEvent | None = None


class StreamWorker:
    def __init__(
        self,
        resolved_source: ResolvedSource,
        alpr,
        event_processor: EventProcessor,
        frame_skip: int = 5,
        reader: SourceReader | None = None,
        predict_func: Callable | None = None,
        extract_func: Callable = extract_plate_results,
        reconnect_delay_seconds: float = 1.0,
        idle_sleep_seconds: float = 0.01,
    ):
        self.resolved_source = resolved_source
        self.alpr = alpr
        self.event_processor = event_processor
        self.frame_skip = max(int(frame_skip), 1)
        self.reader = reader or SourceReader(resolved_source)
        self.predict_func = predict_func or _default_predict_and_annotate
        self.extract_func = extract_func
        self.reconnect_delay_seconds = float(reconnect_delay_seconds)
        self.idle_sleep_seconds = float(idle_sleep_seconds)

        self._thread: threading.Thread | None = None
        self._running = threading.Event()
        self._lock = threading.Lock()
        self._latest_frame = None
        self._status = StreamWorkerStatus(
            camera_id=resolved_source.camera_id,
            camera_name=resolved_source.camera_name,
            running=False,
            connected=False,
            frame_count=0,
            processed_frame_count=0,
        )

    def start(self):
        if self.is_running():
            return

        self._running.set()
        self._set_status(running=True, last_error=None)
        self._thread = threading.Thread(
            target=self.run,
            name=f"stream-worker-{self.resolved_source.camera_id}",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0):
        self._running.clear()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

        self.reader.release()
        self._set_status(running=False, connected=False)

    def run(self, max_frames: int | None = None):
        processed_in_run = 0

        while self._running.is_set():
            if max_frames is not None and processed_in_run >= max_frames:
                break

            try:
                ret, frame = self.reader.read()
            except Exception as exc:
                self.reader.release()
                self._set_status(connected=False, last_error=str(exc))
                time.sleep(self.reconnect_delay_seconds)
                continue

            if not ret:
                self._set_status(connected=False, last_error="Frame tidak tersedia")
                time.sleep(self.reconnect_delay_seconds)
                continue

            self._increment_frame_count()
            self._set_latest_frame(frame)
            self._set_status(connected=True, last_error=None)

            if self.get_status().frame_count % self.frame_skip != 0:
                time.sleep(self.idle_sleep_seconds)
                continue

            self._process_frame(frame)
            processed_in_run += 1
            time.sleep(self.idle_sleep_seconds)

        self.reader.release()
        self._set_status(running=False, connected=False)

    def run_once(self) -> bool:
        was_running = self._running.is_set()
        self._running.set()

        try:
            before = self.get_status().processed_frame_count
            self.run(max_frames=1)
            after = self.get_status().processed_frame_count
            return after > before
        finally:
            if was_running:
                self._running.set()
            else:
                self._running.clear()

    def get_latest_frame(self):
        with self._lock:
            if self._latest_frame is None:
                return None

            return self._latest_frame.copy()

    def get_status(self) -> StreamWorkerStatus:
        with self._lock:
            return StreamWorkerStatus(**self._status.__dict__)

    def is_running(self) -> bool:
        return self._running.is_set() and self._thread is not None and self._thread.is_alive()

    def _process_frame(self, frame):
        annotated_frame, raw_results = self.predict_func(
            alpr=self.alpr,
            frame=frame,
        )
        detections = self.extract_func(raw_results)
        events = self.event_processor.process_detections(
            detections=detections,
            camera_id=self.resolved_source.camera_id,
            camera_name=self.resolved_source.camera_name,
            source_type=self.resolved_source.source_type,
            frame=annotated_frame,
        )

        self._set_latest_frame(annotated_frame)
        self._increment_processed_frame_count()

        if events:
            self._set_status(last_event=events[-1])

    def _set_latest_frame(self, frame):
        with self._lock:
            self._latest_frame = frame.copy()

    def _increment_frame_count(self):
        with self._lock:
            self._status.frame_count += 1

    def _increment_processed_frame_count(self):
        with self._lock:
            self._status.processed_frame_count += 1

    def _set_status(self, **kwargs):
        with self._lock:
            for key, value in kwargs.items():
                setattr(self._status, key, value)


def _default_predict_and_annotate(alpr, frame):
    from core.alpr_engine import predict_and_annotate

    return predict_and_annotate(alpr=alpr, frame=frame)
