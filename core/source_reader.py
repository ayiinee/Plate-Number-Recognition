import cv2

from core.source_resolver import ResolvedSource


class SourceReader:
    def __init__(self, resolved_source: ResolvedSource, loop_demo: bool = True):
        self.resolved_source = resolved_source
        self.loop_demo = loop_demo
        self.cap = None

    def open(self):
        self.cap = cv2.VideoCapture(self.resolved_source.source)

        if not self.cap.isOpened():
            raise RuntimeError(
                f"Source tidak bisa dibuka: {self.resolved_source.camera_id}"
            )

    def read(self):
        if self.cap is None:
            self.open()

        ret, frame = self.cap.read()

        if ret:
            return True, frame

        if self.resolved_source.mode == "demo" and self.loop_demo:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return self.cap.read()

        return False, None

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.release()
