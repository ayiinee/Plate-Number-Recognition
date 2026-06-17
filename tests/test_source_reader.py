import pytest

from core.source_reader import SourceReader
from core.source_resolver import ResolvedSource


def test_source_reader_raises_for_missing_source():
    source = ResolvedSource(
        camera_id="cam_missing",
        camera_name="Missing Camera",
        mode="demo",
        source="data/file_tidak_ada.mp4",
        source_type="demo",
    )
    reader = SourceReader(source)

    with pytest.raises(RuntimeError):
        reader.open()


def test_source_reader_reports_missing_demo_file():
    source = ResolvedSource(
        camera_id="cam_missing",
        camera_name="Missing Camera",
        mode="demo",
        source="data/file_tidak_ada.mp4",
        source_type="demo",
    )
    reader = SourceReader(source)

    with pytest.raises(RuntimeError, match="Video demo tidak ditemukan"):
        reader.open()
