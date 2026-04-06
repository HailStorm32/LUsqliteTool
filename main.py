import logging
import shutil
from pathlib import Path
from tkinter import filedialog

from gui import Application
from logging_config import setup_logging, install_global_exception_logger, get_logger

#########################
# Runtime configuration #
#########################
# Edit these values to control logging and default DB behavior without using CLI args.

# Logging: set level to one of: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL: str = "DEBUG"
# Where to write logs (folder) and the filename
LOG_DIR: str = "logs"
LOG_FILE: str = "lusqlite_tool.log"
# If True, only log to file (no console output). If False, log to file and console.
LOG_FILE_ONLY: bool = False

# Database path: set to a string path to skip the file dialog; set to None to prompt
DB_PATH: str | None = None

# Application version shown in the window title. Update as you release.
APP_VERSION: str = "0.1.0"
# Default window size passed to the GUI on startup. Format: "WIDTHxHEIGHT"
WINDOW_SIZE: str = "1480x900"

def main() -> None:
    """Entry point: configure logging, choose database, and launch Tkinter GUI."""
    # Initialize logging before anything else using in-file constants
    setup_logging(
        log_dir=LOG_DIR,
        log_file=LOG_FILE,
        level=LOG_LEVEL,
        to_console=(not LOG_FILE_ONLY),
    )
    install_global_exception_logger("LUsqliteTool")
    log = get_logger(__name__)

    # Resolve DB file: use CLI if provided, else prompt the user
    if DB_PATH:
        db_file = Path(DB_PATH)
    else:
        selected = filedialog.askopenfilename(
            title="Select LU client SQLite DB",
            filetypes=[("SQLite DB", "*.db *.sqlite *.sqlite3"), ("All", "*.*")],
        )
        if not selected:
            log.info("No database selected - exiting.")
            return
        db_file = Path(selected)

    if not db_file.exists():
        log.error("Database not found: %s", db_file)
        return

    # ---------------------------------------------------------------
    # Backup the database file before opening it.
    # We overwrite any previous backup from a prior session so the user
    # always has a snapshot of the file as it existed at startup.
    # Using copy2 to preserve metadata (timestamps) where possible.
    # ---------------------------------------------------------------
    try:
        backup_path = db_file.with_suffix(db_file.suffix + ".bak")
        shutil.copy2(db_file, backup_path)
        log.info("Database backup created at: %s", backup_path)
    except Exception:
        # Log the failure but continue launching; the backup is a safety net
        log.exception("Failed to create database backup for %s", db_file)

    log.info("Starting application with database: %s", db_file)
    # Pass runtime display settings into the GUI.
    app = Application(db_file, version=APP_VERSION, window_size=WINDOW_SIZE)
    try:
        app.run()
    except Exception:
        # Ensure unexpected GUI failures are captured
        log.exception("Fatal error running application")
        raise


if __name__ == "__main__":
    main()



"""
TODO:
- use the same naming convention for the misision email tab

DestructableCompoent -  DeathBehavior mapping
    https://discord.com/channels/942917763054313552/942924632955174952/1427887339828678713

color1 mapping
    https://explorer.lu-dev.net/misc/brick-colors


    Add the following functionality. Keep readability and maintainability in mind and be sure to leave comments. Also keep in mind to try to commonize when possible to reduce duplicate code when NPC objects are added. Make use of logging for error handling and important events. Log object ID if available.
"""

