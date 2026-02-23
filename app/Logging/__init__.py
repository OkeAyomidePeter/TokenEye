import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging() -> None:
    """
    Configure application-wide logging to write into app/Logging/event_logs.log
    with rotation. Safe to call multiple times.
    """
    log_dir = os.path.dirname(__file__)
    log_path = os.path.join(log_dir, "event_logs.log")

    # Avoid duplicate handlers if reloaded (uvicorn reload)
    root = logging.getLogger()
    if any(isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == os.path.abspath(log_path) for h in root.handlers):
        return

    root.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.WARNING)

    # Also mirror to stderr via basic stream handler under uvicorn if desired
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)

    root.addHandler(file_handler)
    root.addHandler(stream_handler)

