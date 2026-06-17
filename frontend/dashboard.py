from datetime import date
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from core.config import load_config


DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"


st.set_page_config(
    page_title="ANPR Multi Camera Dashboard",
    layout="wide",
)


def api_get(base_url: str, path: str, params: dict | None = None):
    url = build_url(base_url, path, params)

    try:
        with urlopen(url, timeout=5) as response:
            content_type = response.headers.get("Content-Type", "")
            body = response.read()
    except URLError as exc:
        return {
            "success": False,
            "message": f"Backend tidak bisa diakses: {exc}",
            "data": None,
        }

    if "application/json" not in content_type:
        return {
            "success": True,
            "message": "Response non-JSON berhasil diambil.",
            "data": body,
        }

    return json.loads(body.decode("utf-8"))


def api_post(base_url: str, path: str, payload: dict | None = None):
    url = build_url(base_url, path)
    data = json.dumps(payload or {}).encode("utf-8")
    request = Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            body = response.read()
    except URLError as exc:
        return {
            "success": False,
            "message": f"Backend tidak bisa diakses: {exc}",
            "data": None,
        }

    return json.loads(body.decode("utf-8"))


def build_url(base_url: str, path: str, params: dict | None = None) -> str:
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"

    if not params:
        return url

    clean_params = {
        key: value
        for key, value in params.items()
        if value is not None and value != ""
    }

    if not clean_params:
        return url

    return f"{url}?{urlencode(clean_params)}"


def get_camera_configs():
    config = load_config()
    return config.get("sources", {})


def resolve_runtime_camera_configs(local_cameras: dict, health_data: dict | None) -> dict:
    if not health_data:
        return local_cameras

    runtime_cameras = health_data.get("sources") or {}

    if not runtime_cameras:
        return local_cameras

    merged = {
        camera_id: {
            **camera_config,
            **runtime_cameras.get(camera_id, {}),
        }
        for camera_id, camera_config in local_cameras.items()
    }

    for camera_id, camera_config in runtime_cameras.items():
        merged.setdefault(camera_id, camera_config)

    return merged


def render_header():
    st.markdown(
        """
        <div class="main-title">ANPR Multi Camera Dashboard</div>
        <div class="subtitle">Dashboard dua kamera untuk monitoring stream, deteksi plat, dan export CSV.</div>
        """,
        unsafe_allow_html=True,
    )


def render_styles():
    st.markdown(
        """
        <style>
        .main-title {
            color: #111827;
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        .subtitle {
            color: #6B7280;
            font-size: 0.95rem;
            margin-bottom: 1.25rem;
        }
        .metric-tile {
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            padding: 0.875rem 1rem;
            background: #FFFFFF;
        }
        .metric-label {
            color: #6B7280;
            font-size: 0.8rem;
            margin-bottom: 0.25rem;
        }
        .metric-value {
            color: #111827;
            font-size: 1.25rem;
            font-weight: 700;
        }
        .camera-panel {
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            padding: 0.75rem;
            background: #FFFFFF;
        }
        .camera-title {
            color: #111827;
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .status-line {
            color: #4B5563;
            font-size: 0.85rem;
            margin-top: 0.5rem;
        }
        div[data-testid="stSidebar"] {
            background: #FFFFFF;
            border-right: 1px solid #E5E7EB;
        }
        .stButton > button,
        .stDownloadButton > button {
            border-radius: 8px;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_controls(base_url: str, cameras: dict):
    st.sidebar.header("Backend")
    health = api_get(base_url, "/health")
    health_data = health.get("data", {}) if health.get("success") else {}
    runtime_cameras = resolve_runtime_camera_configs(cameras, health_data)

    if health.get("success"):
        st.sidebar.success("Backend aktif")
    else:
        st.sidebar.error("Backend tidak aktif")
        st.sidebar.caption(health.get("message", "Tidak ada detail error."))

    st.sidebar.divider()
    st.sidebar.header("Worker")

    col1, col2 = st.sidebar.columns(2)

    with col1:
        if st.button("Start", use_container_width=True):
            show_api_result(api_post(base_url, "/workers/start"))
            st.rerun()

    with col2:
        if st.button("Stop", use_container_width=True):
            show_api_result(api_post(base_url, "/workers/stop"))
            st.rerun()

    st.sidebar.divider()
    st.sidebar.header("Mode Kamera")

    for camera_id, camera_config in runtime_cameras.items():
        current_mode = str(camera_config.get("mode", "demo"))
        selected_mode = st.sidebar.radio(
            camera_config.get("name", camera_id),
            ["demo", "live"],
            index=0 if current_mode == "demo" else 1,
            horizontal=True,
            key=f"{camera_id}_mode",
        )

        if selected_mode != current_mode:
            show_api_result(
                api_post(
                    base_url,
                    f"/source/{camera_id}/mode",
                    {"mode": selected_mode},
                )
            )
            st.rerun()

    return (
        health_data.get("workers", {}) if health.get("success") else {},
        runtime_cameras,
    )


def render_camera_grid(base_url: str, cameras: dict, worker_status: dict, latest_events: dict):
    camera_columns = st.columns(max(len(cameras), 1))

    for index, (camera_id, camera_config) in enumerate(cameras.items()):
        status = worker_status.get(camera_id, {})
        latest = latest_events.get(camera_id) or {}

        with camera_columns[index]:
            st.markdown('<div class="camera-panel">', unsafe_allow_html=True)
            st.markdown(
                f'<div class="camera-title">{camera_config.get("name", camera_id)}</div>',
                unsafe_allow_html=True,
            )
            render_mjpeg_stream(build_url(base_url, f"/stream/{camera_id}"))
            st.markdown(
                format_camera_status(camera_id, status, latest),
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)


def render_mjpeg_stream(stream_url: str):
    html = f"""
    <img
        src="{stream_url}"
        style="width: 100%; aspect-ratio: 16 / 9; object-fit: contain; background: #111827; border-radius: 8px;"
    />
    """
    components.html(html, height=310)


def format_camera_status(camera_id: str, status: dict, latest: dict) -> str:
    running = "Aktif" if status.get("running") else "Nonaktif"
    connected = "Terhubung" if status.get("connected") else "Belum terhubung"
    last_plate = latest.get("plate_text") or "-"
    confidence = latest.get("confidence")
    last_error = status.get("last_error") or "-"
    inference_ms = status.get("last_inference_ms")
    inference_text = f"{float(inference_ms):.2f} ms" if inference_ms is not None else "-"

    if confidence is not None:
        last_plate = f"{last_plate} ({float(confidence):.2f})"

    return f"""
    <div class="status-line">
        <b>{camera_id}</b> | Worker: {running} | Source: {connected}<br/>
        Frame: {status.get("frame_count", 0)} | Diproses: {status.get("processed_frame_count", 0)}<br/>
        Inference terakhir: {inference_text}<br/>
        Plat terakhir: {last_plate}<br/>
        Error terakhir: {last_error}
    </div>
    """


def render_summary(events_df: pd.DataFrame, latest_events: dict):
    total_records = len(events_df)
    unique_plates = events_df["plate_text"].nunique() if not events_df.empty else 0
    latest_plate = "-"

    if latest_events:
        latest_rows = [row for row in latest_events.values() if row]

        if latest_rows:
            latest_rows = sorted(latest_rows, key=lambda row: row.get("timestamp", ""))
            latest_plate = latest_rows[-1].get("plate_text", "-")

    col1, col2, col3 = st.columns(3)

    with col1:
        metric_tile("Total Record", total_records)

    with col2:
        metric_tile("Plat Unik", unique_plates)

    with col3:
        metric_tile("Deteksi Terakhir", latest_plate)


def metric_tile(label: str, value):
    st.markdown(
        f"""
        <div class="metric-tile">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_events_table(base_url: str, cameras: dict, min_confidence: float):
    events_response = api_get(
        base_url,
        "/events",
        {"limit": 1000, "min_confidence": min_confidence},
    )
    latest_response = api_get(base_url, "/events/latest")

    events = events_response.get("data") if events_response.get("success") else []
    latest_events = latest_response.get("data") if latest_response.get("success") else {}
    df = pd.DataFrame(events or [])

    render_summary(df, latest_events)
    st.subheader("Riwayat Deteksi")

    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 2])

    with filter_col1:
        camera_options = ["Semua"] + list(cameras.keys())
        selected_camera = st.selectbox("Kamera", camera_options)

    with filter_col2:
        selected_date = st.date_input("Tanggal", value=None)

    with filter_col3:
        keyword = st.text_input("Cari plat", placeholder="Contoh: B1234CD")

    filtered_df = filter_events_dataframe(
        df=df,
        camera_id=selected_camera,
        selected_date=selected_date,
        keyword=keyword,
    )

    if filtered_df.empty:
        st.info("Belum ada record yang cocok dengan filter.")
    else:
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

    csv_response = api_get(
        base_url,
        "/export/csv",
        {"min_confidence": min_confidence},
    )
    csv_bytes = csv_response.get("data") if csv_response.get("success") else b""

    st.download_button(
        label="Download CSV",
        data=csv_bytes,
        file_name="hasil_deteksi_plat.csv",
        mime="text/csv",
        disabled=not bool(csv_bytes),
    )

    return latest_events


def filter_events_dataframe(
    df: pd.DataFrame,
    camera_id: str,
    selected_date: date | None,
    keyword: str,
) -> pd.DataFrame:
    if df.empty:
        return df

    filtered_df = df.copy()

    if camera_id != "Semua" and "camera_id" in filtered_df:
        filtered_df = filtered_df[filtered_df["camera_id"] == camera_id]

    if selected_date is not None and "timestamp" in filtered_df:
        date_text = selected_date.strftime("%Y-%m-%d")
        filtered_df = filtered_df[
            filtered_df["timestamp"].astype(str).str.startswith(date_text)
        ]

    if keyword and "plate_text" in filtered_df:
        keyword = keyword.upper().strip()
        filtered_df = filtered_df[
            filtered_df["plate_text"].astype(str).str.upper().str.contains(keyword)
        ]

    return filtered_df.reset_index(drop=True)


def show_api_result(response: dict):
    if response.get("success"):
        st.toast(response.get("message", "Berhasil."))
    else:
        st.error(response.get("message", "Request gagal."))


def main():
    render_styles()
    render_header()

    st.sidebar.header("Pengaturan")
    base_url = st.sidebar.text_input("Backend URL", value=DEFAULT_BACKEND_URL)
    min_confidence = st.sidebar.slider(
        "Minimum confidence",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.05,
    )
    if st.sidebar.button("Refresh Data", use_container_width=True):
        st.rerun()

    local_cameras = get_camera_configs()
    worker_status, cameras = render_controls(base_url, local_cameras)
    latest_events = render_events_table(base_url, cameras, min_confidence)
    render_camera_grid(base_url, cameras, worker_status, latest_events)


if __name__ == "__main__":
    main()
