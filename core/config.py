from pathlib import Path
from copy import deepcopy
from typing import Any


DEFAULT_CONFIG_PATH = Path("config.yaml")


DEFAULT_CONFIG = {
    "app": {
        "name": "ANPR Multi Camera System",
        "environment": "development",
    },
    "model": {
        "detector": "yolo-v9-t-384-license-plate-end2end",
        "ocr": "cct-xs-v2-global-model",
        "provider": "cpu",
    },
    "processing": {
        "frame_skip": 5,
        "min_confidence": 0.70,
        "cooldown_seconds": 5,
        "queue_size": 2,
    },
    "storage": {
        "database_path": "outputs/detections.db",
        "snapshot_dir": "outputs/snapshots",
    },
    "sources": {
        "cam_1": {
            "name": "Kamera 1 - Gate Masuk",
            "mode": "demo",
            "live_url": "rtsp://user:password@192.168.1.10/stream",
            "demo_path": "data/demo_cam_1.mp4",
        },
        "cam_2": {
            "name": "Kamera 2 - Gate Keluar",
            "mode": "demo",
            "live_url": "rtsp://user:password@192.168.1.11/stream",
            "demo_path": "data/demo_cam_2.mp4",
        },
    },
}


def load_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    path = Path(config_path)

    if not path.exists():
        return deepcopy(DEFAULT_CONFIG)

    text = path.read_text(encoding="utf-8")

    try:
        import yaml

        loaded = yaml.safe_load(text) or {}
    except ImportError:
        loaded = _parse_simple_yaml(text)

    return _merge_dicts(DEFAULT_CONFIG, loaded)


def _merge_dicts(
    base: dict[str, Any],
    override: dict[str, Any],
) -> dict[str, Any]:
    merged = deepcopy(base)

    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value

    return merged


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]

        if value == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(value)

    return root


def _parse_scalar(value: str) -> Any:
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"

    if value.lower() in {"null", "none"}:
        return None

    try:
        if "." in value:
            return float(value)

        return int(value)
    except ValueError:
        return value.strip("\"'")
