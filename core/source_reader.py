import logging
from pathlib import Path

import cv2

from core.source_resolver import ResolvedSource


logger = logging.getLogger(__name__)


class SourceReader:
    def __init__(self, resolved_source: ResolvedSource, loop_demo: bool = True):
        self.resolved_source = resolved_source
        self.loop_demo = loop_demo
        self.cap = None

    def open(self):
        if self.resolved_source.mode == "demo":
            demo_path = Path(self.resolved_source.source)

            if not demo_path.exists():
                message = f"Video demo tidak ditemukan: {demo_path}"
                logger.error(
                    "%s camera_id=%s",
                    message,
                    self.resolved_source.camera_id,
                )
                raise RuntimeError(message)

        logger.info(
            "Membuka source camera_id=%s mode=%s source=%s",
            self.resolved_source.camera_id,
            self.resolved_source.mode,
            self.resolved_source.source,
        )
        self.cap = cv2.VideoCapture(self.resolved_source.source)

        if not self.cap.isOpened():
            logger.error(
                "Source tidak bisa dibuka camera_id=%s source=%s",
                self.resolved_source.camera_id,
                self.resolved_source.source,
            )
            raise RuntimeError(
                f"Source tidak bisa dibuka: {self.resolved_source.camera_id} ({self.resolved_source.source})"
            )

    def read(self):
        if self.cap is None:
            self.open()

        ret, frame = self.cap.read()

        if ret:
            return True, frame

        if self.resolved_source.mode == "demo" and self.loop_demo:
            logger.info(
                "Video demo selesai, loop ulang camera_id=%s",
                self.resolved_source.camera_id,
            )
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return self.cap.read()

        return False, None

    def release(self):
        if self.cap is not None:
            logger.info("Menutup source camera_id=%s", self.resolved_source.camera_id)
            self.cap.release()
            self.cap = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.release()
