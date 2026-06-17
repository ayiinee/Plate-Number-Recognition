import pandas as pd

from frontend.dashboard import build_url, filter_events_dataframe


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
