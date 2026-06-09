import queue

import av
from streamlit_webrtc import VideoProcessorBase

from core.alpr_engine import predict_and_annotate
from core.plate_parser import extract_plate_results


class ALPRVideoProcessor(VideoProcessorBase):
    def __init__(self, alpr, min_confidence):
        self.alpr = alpr
        self.min_confidence = min_confidence
        self.result_queue = queue.Queue()

    def recv(self, frame):
        image = frame.to_ndarray(format="bgr24")

        annotated_frame, results = predict_and_annotate(
            alpr=self.alpr,
            frame=image,
        )

        detections = extract_plate_results(results)

        for detection in detections:
            if detection["confidence"] >= self.min_confidence:
                self.result_queue.put(detection)

        return av.VideoFrame.from_ndarray(
            annotated_frame,
            format="bgr24",
        )

    def get_pending_results(self):
        pending = []

        while not self.result_queue.empty():
            pending.append(self.result_queue.get())

        return pending