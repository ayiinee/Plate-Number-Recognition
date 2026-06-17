import pandas as pd

from frontend.dashboard import (
    build_url,
    filter_events_dataframe,
    format_camera_status,
    resolve_runtime_camera_configs,
)


def test_build_url_skips_empty_params():
    url = build_url(
        "http://127.0.0.1:8000/",
        "/events",
        {"limit": 100, "min_confidence": None, "keyword": ""},
    )

    assert url == "http://127.0.0.1:8000/events?limit=100"


def test_filter_events_dataframe_by_camera_date_and_keyword():
    df = pd.DataFrame(
        [
            {
                "timestamp": "2026-06-17 10:00:00",
                "camera_id": "cam_1",
                "plate_text": "B1234CD",
            },
            {
                "timestamp": "2026-06-18 10:00:00",
                "camera_id": "cam_2",
                "plate_text": "D5678EF",
            },
        ]
    )

    filtered = filter_events_dataframe(
        df=df,
        camera_id="cam_1",
        selected_date=pd.Timestamp("2026-06-17").date(),
        keyword="b123",
    )

    assert len(filtered) == 1
    assert filtered.iloc[0]["plate_text"] == "B1234CD"


def test_format_camera_status_includes_error_and_inference():
    html = format_camera_status(
        "cam_1",
        {
            "running": True,
            "connected": False,
            "frame_count": 10,
            "processed_frame_count": 2,
            "last_inference_ms": 12.34,
            "last_error": "Video demo tidak ditemukan",
        },
        {"plate_text": "B1234CD", "confidence": 0.9},
    )

    assert "12.34 ms" in html
    assert "Video demo tidak ditemukan" in html
    assert "B1234CD (0.90)" in html


def test_resolve_runtime_camera_configs_prefers_backend_mode():
    cameras = {
        "cam_1": {
            "name": "Kamera 1",
            "mode": "demo",
            "demo_path": "data/demo_cam_1.mp4",
        }
    }
    health_data = {
        "sources": {
            "cam_1": {
                "mode": "live",
                "live_url": "rtsp://example/stream",
            }
        }
    }

    resolved = resolve_runtime_camera_configs(cameras, health_data)

    assert resolved["cam_1"]["mode"] == "live"
    assert resolved["cam_1"]["demo_path"] == "data/demo_cam_1.mp4"
