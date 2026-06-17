from pathlib import Path

from core.config import load_config
from core.source_resolver import SourceResolver


def test_load_config_reads_sources():
    config = load_config()

    assert "cam_1" in config["sources"]
    assert "cam_2" in config["sources"]


def test_source_resolver_uses_demo_path():
    config = {
        "sources": {
            "cam_1": {
                "name": "Kamera 1",
                "mode": "demo",
                "live_url": "rtsp://example/stream",
                "demo_path": "data/demo_cam_1.mp4",
            }
        }
    }
    resolver = SourceResolver(config)

    source = resolver.resolve("cam_1")

    assert source.camera_id == "cam_1"
    assert source.camera_name == "Kamera 1"
    assert source.source == "data/demo_cam_1.mp4"
    assert source.source_type == "demo"


def test_source_resolver_can_switch_to_live():
    config = {
        "sources": {
            "cam_1": {
                "name": "Kamera 1",
                "mode": "demo",
                "live_url": "rtsp://example/stream",
                "demo_path": "data/demo_cam_1.mp4",
            }
        }
    }
    resolver = SourceResolver(config)

    resolver.set_mode("cam_1", "live")
    source = resolver.resolve("cam_1")

    assert source.source == "rtsp://example/stream"
    assert source.source_type == "live"


def test_load_config_supports_custom_yaml():
    config_path = Path(".tmp") / "test_config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        """
sources:
  cam_1:
    name: Custom Camera
    mode: live
    live_url: rtsp://custom/stream
    demo_path: data/custom.mp4
""",
        encoding="utf-8",
    )

    config = load_config(config_path)
    source = SourceResolver(config).resolve("cam_1")

    assert source.camera_name == "Custom Camera"
    assert source.source == "rtsp://custom/stream"
