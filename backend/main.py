import time
import logging
from dataclasses import asdict, is_dataclass
from typing import Any

import cv2
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from core.logging_config import configure_logging
from core.stream_manager import StreamManager


configure_logging()
logger = logging.getLogger(__name__)
app = FastAPI(title="ANPR Multi Camera Backend")
manager = StreamManager()


class SourceModeRequest(BaseModel):
    mode: str


def api_response(success: bool, message: str, data: Any = None):
    return {
        "success": success,
        "message": message,
        "data": data,
    }


def serialize(value: Any):
    if is_dataclass(value):
        return serialize(asdict(value))

    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}

    if isinstance(value, list):
        return [serialize(item) for item in value]

    return value


@app.get("/health")
def health():
    return api_response(
        success=True,
        message="Backend aktif.",
        data={
            "service": "anpr-backend",
            "sources": serialize(manager.config.get("sources", {})),
            "workers": serialize(manager.get_status()),
        },
    )


@app.post("/workers/start")
def start_workers():
    try:
        manager.start_all()
        logger.info("Semua worker kamera dijalankan")
    except Exception as exc:
        logger.exception("Gagal menjalankan semua worker")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return api_response(
        success=True,
        message="Semua worker kamera dijalankan.",
        data=serialize(manager.get_status()),
    )


@app.post("/workers/stop")
def stop_workers():
    manager.stop_all()
    logger.info("Semua worker kamera dihentikan")

    return api_response(
        success=True,
        message="Semua worker kamera dihentikan.",
        data=serialize(manager.get_status()),
    )


@app.post("/workers/{camera_id}/start")
def start_worker(camera_id: str):
    try:
        manager.start_worker(camera_id)
        logger.info("Worker dijalankan camera_id=%s", camera_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Gagal menjalankan worker camera_id=%s", camera_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return api_response(
        success=True,
        message=f"Worker {camera_id} dijalankan.",
        data=serialize(manager.get_status().get(camera_id)),
    )


@app.post("/workers/{camera_id}/stop")
def stop_worker(camera_id: str):
    manager.stop_worker(camera_id)
    logger.info("Worker dihentikan camera_id=%s", camera_id)

    return api_response(
        success=True,
        message=f"Worker {camera_id} dihentikan.",
        data=serialize(manager.get_status().get(camera_id)),
    )


@app.get("/events")
def get_events(limit: int = 100, min_confidence: float | None = None):
    rows = manager.storage.get_detections(
        limit=limit,
        min_confidence=min_confidence,
    )

    return api_response(
        success=True,
        message="Riwayat deteksi berhasil diambil.",
        data=rows,
    )


@app.get("/events/latest")
def get_latest_events():
    latest_events = {}

    for camera_id in manager.config.get("sources", {}):
        latest_events[camera_id] = manager.storage.get_latest_by_camera(camera_id)

    return api_response(
        success=True,
        message="Deteksi terbaru per kamera berhasil diambil.",
        data=latest_events,
    )


@app.get("/export/csv")
def export_csv(min_confidence: float | None = None):
    csv_bytes = manager.storage.export_csv(min_confidence=min_confidence)

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=hasil_deteksi_plat.csv"
        },
    )


@app.post("/source/{camera_id}/mode")
def set_source_mode(camera_id: str, request: SourceModeRequest):
    try:
        manager.set_mode(camera_id, request.mode)
        resolved_source = manager.resolver.resolve(camera_id)
        logger.info("Mode source diubah camera_id=%s mode=%s", camera_id, request.mode)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return api_response(
        success=True,
        message=f"Mode {camera_id} diubah ke {resolved_source.mode}.",
        data=serialize(resolved_source),
    )


@app.get("/stream/{camera_id}")
def stream_camera(camera_id: str):
    if camera_id not in manager.config.get("sources", {}):
        raise HTTPException(status_code=404, detail=f"Kamera tidak ditemukan: {camera_id}")

    return StreamingResponse(
        _mjpeg_frame_generator(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


def _mjpeg_frame_generator(camera_id: str):
    while True:
        frame = manager.get_latest_frame(camera_id)

        if frame is None:
            time.sleep(0.1)
            continue

        success, encoded = cv2.imencode(".jpg", frame)

        if not success:
            time.sleep(0.1)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + encoded.tobytes()
            + b"\r\n"
        )
        time.sleep(0.03)
