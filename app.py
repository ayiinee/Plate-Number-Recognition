import time

import cv2
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration

from core.alpr_engine import create_alpr_engine, predict_and_annotate
from core.plate_parser import extract_plate_results
from core.record_store import PlateRecordStore
from core.video_file import save_uploaded_video, open_video_source, get_total_frames
from core.webrtc_processor import ALPRVideoProcessor
from ui.styles import apply_custom_styles


st.set_page_config(
    page_title="ALPR Dashboard",
    layout="wide",
)


@st.cache_resource
def load_model():
    return create_alpr_engine()


def init_session_state():
    if "record_store" not in st.session_state:
        st.session_state.record_store = PlateRecordStore()


def render_header():
    st.markdown(
        """
        <div class="main-title">Automatic License Plate Recognition</div>
        <div class="subtitle">
        Aplikasi deteksi plat nomor kendaraan dari kamera live atau video, dengan pencatatan hasil ke CSV.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_summary(df):
    total_records = len(df)
    unique_plates = df["plat_nomor"].nunique() if not df.empty else 0
    last_plate = df.iloc[-1]["plat_nomor"] if not df.empty else "-"

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""
            <div class="section-card">
                <div class="metric-label">Total Record</div>
                <div class="metric-value">{total_records}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="section-card">
                <div class="metric-label">Plat Unik</div>
                <div class="metric-value">{unique_plates}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="section-card">
                <div class="metric-label">Deteksi Terakhir</div>
                <div class="metric-value">{last_plate}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_records_panel():
    store = st.session_state.record_store
    df = store.to_dataframe()

    st.subheader("Record Plat Nomor")
    render_summary(df)

    if df.empty:
        st.info("Belum ada plat nomor yang tercatat.")
    else:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            label="Download CSV",
            data=store.to_csv_bytes(),
            file_name="hasil_deteksi_plat.csv",
            mime="text/csv",
        )

    if st.button("Hapus Semua Record"):
        store.clear()
        st.rerun()


def render_sidebar():
    st.sidebar.header("Pengaturan")

    input_mode = st.sidebar.radio(
        "Sumber input",
        ["Kamera Live", "Upload Video", "Path Video / RTSP"],
    )

    min_confidence = st.sidebar.slider(
        "Minimum confidence OCR",
        min_value=0.00,
        max_value=1.00,
        value=0.50,
        step=0.05,
    )

    cooldown_seconds = st.sidebar.slider(
        "Jeda pencatatan plat yang sama",
        min_value=1,
        max_value=30,
        value=5,
    )

    frame_skip = st.sidebar.slider(
        "Proses setiap beberapa frame",
        min_value=1,
        max_value=10,
        value=3,
    )

    return input_mode, min_confidence, cooldown_seconds, frame_skip


def run_uploaded_or_path_video(
    source,
    source_name,
    alpr,
    min_confidence,
    cooldown_seconds,
    frame_skip,
):
    store = st.session_state.record_store

    video_placeholder = st.empty()
    progress_placeholder = st.empty()
    status_placeholder = st.empty()

    try:
        cap = open_video_source(source)
    except RuntimeError:
        st.error("Video tidak bisa dibuka. Periksa file, path, atau RTSP URL.")
        return

    total_frames = get_total_frames(cap)
    frame_counter = 0

    status_placeholder.info("Pemrosesan video berjalan.")

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        frame_counter += 1

        if frame_counter % frame_skip != 0:
            continue

        annotated_frame, results = predict_and_annotate(
            alpr=alpr,
            frame=frame,
        )

        detections = extract_plate_results(results)

        store.add_many(
            detections=detections,
            source_name=source_name,
            min_confidence=min_confidence,
            cooldown_seconds=cooldown_seconds,
        )

        annotated_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)

        video_placeholder.image(
            annotated_rgb,
            channels="RGB",
            use_container_width=True,
        )

        if total_frames > 0:
            progress = min(frame_counter / total_frames, 1.0)
            progress_placeholder.progress(progress)

        time.sleep(0.02)

    cap.release()
    progress_placeholder.progress(1.0)
    status_placeholder.success("Pemrosesan video selesai.")


def render_camera_live(alpr, min_confidence, cooldown_seconds):
    st.subheader("Kamera Live")

    rtc_configuration = RTCConfiguration(
    {
        "iceServers": [
            {
                "urls": [
                    "stun:stun.l.google.com:19302",
                    "stun:stun1.l.google.com:19302",
                    "stun:stun2.l.google.com:19302",
                    "stun:stun3.l.google.com:19302",
                    "stun:stun4.l.google.com:19302",
                ]
            }
        ]
    }
)

    ctx = webrtc_streamer(
        key="alpr-camera",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=rtc_configuration,
        media_stream_constraints={
            "video": True,
            "audio": False,
        },
        video_processor_factory=lambda: ALPRVideoProcessor(
            alpr=alpr,
            min_confidence=min_confidence,
        ),
        async_processing=True,
    )

    result_placeholder = st.empty()

    if ctx.video_processor:
        while ctx.state.playing:
            detections = ctx.video_processor.get_pending_results()

            if detections:
                st.session_state.record_store.add_many(
                    detections=detections,
                    source_name="Kamera Live",
                    min_confidence=min_confidence,
                    cooldown_seconds=cooldown_seconds,
                )

            df = st.session_state.record_store.to_dataframe()

            with result_placeholder.container():
                if df.empty:
                    st.info("Belum ada plat nomor yang tercatat dari kamera.")
                else:
                    st.dataframe(
                        df.tail(10),
                        use_container_width=True,
                        hide_index=True,
                    )

            time.sleep(1)


def render_video_upload(alpr, min_confidence, cooldown_seconds, frame_skip):
    st.subheader("Upload Video")

    uploaded_file = st.file_uploader(
        "Pilih file video",
        type=["mp4", "avi", "mov", "mkv"],
    )

    if uploaded_file is None:
        st.info("Upload file video terlebih dahulu.")
        return

    if st.button("Proses Video"):
        video_path = save_uploaded_video(uploaded_file)

        run_uploaded_or_path_video(
            source=video_path,
            source_name=uploaded_file.name,
            alpr=alpr,
            min_confidence=min_confidence,
            cooldown_seconds=cooldown_seconds,
            frame_skip=frame_skip,
        )


def render_path_or_rtsp(alpr, min_confidence, cooldown_seconds, frame_skip):
    st.subheader("Path Video atau RTSP")

    source = st.text_input(
        "Masukkan path video atau RTSP URL",
        value="tes.mp4",
    )

    if st.button("Mulai Proses"):
        run_uploaded_or_path_video(
            source=source,
            source_name=source,
            alpr=alpr,
            min_confidence=min_confidence,
            cooldown_seconds=cooldown_seconds,
            frame_skip=frame_skip,
        )


def main():
    apply_custom_styles()
    init_session_state()

    alpr = load_model()

    render_header()

    input_mode, min_confidence, cooldown_seconds, frame_skip = render_sidebar()

    left_col, right_col = st.columns([2, 1])

    with left_col:
        if input_mode == "Kamera Live":
            render_camera_live(
                alpr=alpr,
                min_confidence=min_confidence,
                cooldown_seconds=cooldown_seconds,
            )

        elif input_mode == "Upload Video":
            render_video_upload(
                alpr=alpr,
                min_confidence=min_confidence,
                cooldown_seconds=cooldown_seconds,
                frame_skip=frame_skip,
            )

        else:
            render_path_or_rtsp(
                alpr=alpr,
                min_confidence=min_confidence,
                cooldown_seconds=cooldown_seconds,
                frame_skip=frame_skip,
            )

    with right_col:
        render_records_panel()


if __name__ == "__main__":
    main()