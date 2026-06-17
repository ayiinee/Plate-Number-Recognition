import logging
from pathlib import Path


DEFAULT_LOG_PATH = Path("outputs") / "logs" / "anpr.log"


def configure_logging(log_path: str | Path = DEFAULT_LOG_PATH):
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.FileHandler(path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=False,
    )
