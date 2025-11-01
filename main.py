import logging
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

    log.info("Starting application with database: %s", db_file)
    app = Application(db_file)
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
- NPC functionality
   - domains
   - repository
   - service
   - GUI
- Pull ColorType values from DB (BrickColors table) instead of hardcoding


DestructableCompoent -  DeathBehavior mapping
    https://discord.com/channels/942917763054313552/942924632955174952/1427887339828678713

color1 mapping
    https://explorer.lu-dev.net/misc/brick-colors


    Add the following functionality. Keep readability and maintainability in mind and be sure to leave comments. Also keep in mind to try to commonize when possible to reduce duplicate code when NPC objects are added
"""

