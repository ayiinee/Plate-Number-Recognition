import time
from dataclasses import dataclass, asdict
from datetime import datetime

import pandas as pd


@dataclass
class PlateRecord:
    waktu: str
    sumber: str
    plat_nomor: str
    confidence: float


class PlateRecordStore:
    def __init__(self):
        self.records = []
        self.last_seen = {}

    def add_detection(
        self,
        plate: str,
        confidence: float,
        source_name: str,
        min_confidence: float,
        cooldown_seconds: int,
    ):
        confidence = float(confidence)
        min_confidence = float(min_confidence)

        if confidence < min_confidence:
            return

        now = time.time()
        last_time = self.last_seen.get(plate, 0)

        if now - last_time < cooldown_seconds:
            return

        self.last_seen[plate] = now

        record = PlateRecord(
            waktu=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            sumber=source_name,
            plat_nomor=plate,
            confidence=round(confidence, 4),
        )

        self.records.append(asdict(record))

    def add_many(
        self,
        detections,
        source_name: str,
        min_confidence: float,
        cooldown_seconds: int,
    ):
        for detection in detections:
            self.add_detection(
                plate=detection["plate"],
                confidence=detection["confidence"],
                source_name=source_name,
                min_confidence=min_confidence,
                cooldown_seconds=cooldown_seconds,
            )

    def to_dataframe(self, min_confidence: float | None = None):
        df = pd.DataFrame(self.records)

        if min_confidence is None or df.empty:
            return df

        return df[df["confidence"] >= float(min_confidence)].reset_index(drop=True)

    def to_csv_bytes(self, min_confidence: float | None = None):
        df = self.to_dataframe(min_confidence=min_confidence)
        return df.to_csv(index=False).encode("utf-8")

    def clear(self):
        self.records = []
        self.last_seen = {}
