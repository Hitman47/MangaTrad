from __future__ import annotations

import faulthandler
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType

_LOGGER_READY = False
_FATAL_HANDLE = None


def default_log_dir() -> Path:
    return Path.cwd() / "logs"


def setup_app_logging(log_dir: str | Path | None = None) -> tuple[Path, Path]:
    """Configure application logging and native-crash faulthandler dumps.

    Returns ``(app_log_path, fatal_log_path)``. The fatal log is intentionally
    separate because native OCR/ML libraries can terminate the process before a
    Python exception is raised.
    """

    global _LOGGER_READY, _FATAL_HANDLE
    base_dir = Path(log_dir or os.environ.get("MANGATRAD_LOG_DIR") or default_log_dir())
    base_dir.mkdir(parents=True, exist_ok=True)
    app_log = base_dir / "mangatrad.log"
    fatal_log = base_dir / "mangatrad_fatal.log"

    handlers: list[logging.Handler] = [
        RotatingFileHandler(app_log, maxBytes=2_000_000, backupCount=5, encoding="utf-8"),
        logging.StreamHandler(sys.stderr),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
    _LOGGER_READY = True

    try:
        if _FATAL_HANDLE is not None:
            _FATAL_HANDLE.close()
        _FATAL_HANDLE = fatal_log.open("a", encoding="utf-8")
        faulthandler.enable(file=_FATAL_HANDLE, all_threads=True)
    except Exception:  # pragma: no cover - logging must never block startup
        logging.getLogger(__name__).exception("Unable to enable faulthandler")

    def _excepthook(
        exc_type: type[BaseException],
        exc: BaseException,
        tb: TracebackType | None,
    ) -> None:
        logging.getLogger("cbz_manga_translator.unhandled").exception(
            "Unhandled exception", exc_info=(exc_type, exc, tb)
        )
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _excepthook
    logging.getLogger(__name__).info("Logging initialized: app=%s fatal=%s", app_log, fatal_log)
    return app_log, fatal_log


def logging_ready() -> bool:
    return _LOGGER_READY
