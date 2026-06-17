from dataclasses import dataclass
from typing import Any


@dataclass
class ResolvedSource:
    camera_id: str
    camera_name: str
    mode: str
    source: str
    source_type: str


class SourceResolver:
    def __init__(self, config: dict[str, Any]):
        self.config = config

    def resolve(self, camera_id: str) -> ResolvedSource:
        sources = self.config.get("sources", {})
        source_config = sources.get(camera_id)

        if source_config is None:
            raise KeyError(f"Camera source tidak ditemukan: {camera_id}")

        mode = str(source_config.get("mode", "demo")).lower()

        if mode == "demo":
            source = source_config.get("demo_path")
        elif mode == "live":
            source = source_config.get("live_url")
        else:
            raise ValueError(f"Mode source tidak didukung: {mode}")

        if not source:
            raise ValueError(f"Source untuk {camera_id} mode {mode} belum diisi")

        return ResolvedSource(
            camera_id=camera_id,
            camera_name=source_config.get("name", camera_id),
            mode=mode,
            source=source,
            source_type=mode,
        )

    def set_mode(self, camera_id: str, mode: str):
        mode = mode.lower()

        if mode not in {"demo", "live"}:
            raise ValueError(f"Mode source tidak didukung: {mode}")

        sources = self.config.setdefault("sources", {})

        if camera_id not in sources:
            raise KeyError(f"Camera source tidak ditemukan: {camera_id}")

        sources[camera_id]["mode"] = mode
