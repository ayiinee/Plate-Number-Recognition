import tempfile
import cv2


def save_uploaded_video(uploaded_file):
    """
    Streamlit uploader menghasilkan file-like object.
    OpenCV lebih aman membaca dari temporary file path.
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    temp_file.write(uploaded_file.read())
    temp_file.close()

    return temp_file.name


def open_video_source(source):
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        raise RuntimeError("Sumber video tidak bisa dibuka.")

    return cap


def get_total_frames(cap):
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if total_frames < 0:
        return 0

    return total_frames