"""
Centralized logging setup for LUsqliteTool.

Highlights:
- File logging with daily rotation (keeps 14 days by default)
- Optional console logging (toggle on/off)
- Configurable log level via (1) function args, (2) environment variables, or (3) in-file defaults
- Rich, production-friendly format including timestamp, level, module, line, and function
- Safe to call multiple times; reconfigures handlers if needed
- Installs a global excepthook to ensure uncaught exceptions are logged

Configuration precedence (highest first):
1) Function arguments to setup_logging
2) Environment variables (optional):
    - LU_LOG_LEVEL        (default from in-file: DEFAULT_LOG_LEVEL)   e.g., DEBUG/INFO/WARNING/ERROR/CRITICAL
    - LU_LOG_DIR          (default from in-file: DEFAULT_LOG_DIR)
    - LU_LOG_FILE         (default from in-file: DEFAULT_LOG_FILE)
    - LU_LOG_TO_CONSOLE   (default from in-file: DEFAULT_LOG_TO_CONSOLE)   1/true/on or 0/false/off
    - LU_LOG_RETENTION    (default from in-file: DEFAULT_LOG_RETENTION)    number of daily rotated files to keep
3) In-file defaults (edit the constants below)
"""
from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional

# -----------------------------
# In-file defaults (editable)
# -----------------------------
DEFAULT_LOG_LEVEL: str = "INFO"
DEFAULT_LOG_DIR: str = "logs"
DEFAULT_LOG_FILE: str = "lusqlite_tool.log"
DEFAULT_LOG_TO_CONSOLE: bool = True
DEFAULT_LOG_RETENTION: int = 14


DEFAULT_LOG_FORMAT: str = (
    "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(funcName)s | %(message)s"
)

# Internal alias used as the function default; users can edit DEFAULT_LOG_FORMAT above
_DEFAULT_FORMAT = DEFAULT_LOG_FORMAT


def _parse_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    v = value.strip().lower()
    return v in {"1", "true", "t", "yes", "y", "on"}


def _level_from_str(level: str | int | None, fallback: int = logging.INFO) -> int:
    if level is None:
        return fallback
    if isinstance(level, int):
        return level
    try:
        return getattr(logging, str(level).upper())
    except Exception:
        return fallback


def setup_logging(
    *,
    log_dir: str | Path | None = None,
    log_file: str | Path | None = None,
    level: str | int | None = None,
    to_console: bool | None = None,
    retention_days: int | None = None,
    fmt: str = _DEFAULT_FORMAT,
) -> None:
    """
    Configure root logging with a rotating file handler and optional console handler.

    Call this as early as possible (e.g., at the start of main()).

    Args:
        log_dir: Directory to store logs (default from env LU_LOG_DIR or 'logs').
        log_file: File name (default from env LU_LOG_FILE or 'lusqlite_tool.log').
        level: Log level (string or int). Defaults to env LU_LOG_LEVEL or logging.INFO.
        to_console: When True, add a console handler; when False, file only.
                    Defaults to env LU_LOG_TO_CONSOLE (true-ish) or True.
        retention_days: Daily rotation retention (default env LU_LOG_RETENTION or 14).
        fmt: Log format string.
    """
    # Resolve settings with precedence: args > env > in-file defaults
    log_dir = Path(log_dir or os.getenv("LU_LOG_DIR", DEFAULT_LOG_DIR))
    log_file = Path(log_file or os.getenv("LU_LOG_FILE", DEFAULT_LOG_FILE))

    level_str: str | int | None = level if level is not None else os.getenv("LU_LOG_LEVEL", DEFAULT_LOG_LEVEL)
    level_num = _level_from_str(level_str, logging.INFO)

    if to_console is None:
        env_console = os.getenv("LU_LOG_TO_CONSOLE")
        to_console = _parse_bool(env_console, DEFAULT_LOG_TO_CONSOLE)
    else:
        to_console = bool(to_console)

    if retention_days is None:
        retention = int(os.getenv("LU_LOG_RETENTION", str(DEFAULT_LOG_RETENTION)))
    else:
        retention = int(retention_days)

    # Ensure log directory exists
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Fall back to current directory if we can't create the specified one
        log_dir = Path('.')

    logfile_path = log_dir / log_file

    # Create formatter
    formatter = logging.Formatter(fmt)

    # Build handlers
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=str(logfile_path),
        when="midnight",
        backupCount=max(0, retention),
        encoding="utf-8",
        utc=False,
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level_num)

    handlers: list[logging.Handler] = [file_handler]

    if to_console:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.setLevel(level_num)
        handlers.append(console)

    # Reconfigure root logger atomically
    root = logging.getLogger()
    root.setLevel(level_num)

    # Remove existing handlers to avoid duplicates on repeated calls
    for h in list(root.handlers):
        try:
            root.removeHandler(h)
            h.close()
        except Exception:
            pass

    for h in handlers:
        root.addHandler(h)

    # Reduce noise from third-party libraries if necessary (example)
    logging.getLogger("sqlite3").setLevel(max(level_num, logging.WARNING))


def install_global_exception_logger(logger_name: str = "app") -> None:
    """Install a sys.excepthook that logs uncaught exceptions to the given logger.

    Useful for GUI apps where exceptions might otherwise be swallowed.
    """
    import sys

    log = logging.getLogger(logger_name)

    def _hook(exc_type, exc_value, exc_traceback):
        try:
            if issubclass(exc_type, KeyboardInterrupt):
                # Respect Ctrl+C without a noisy stack trace
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            log.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
        except Exception:
            # Last resort: delegate to default hook
            sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = _hook


def get_logger(name: str) -> logging.Logger:
    """Convenience helper to get a named logger."""
    return logging.getLogger(name)
