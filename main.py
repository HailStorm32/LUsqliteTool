import sys
from pathlib import Path
from tkinter import filedialog

from gui import Application


def main() -> None:
    """Entry point: choose database and launch Tkinter GUI."""
    if len(sys.argv) > 1:
        db_file = Path(sys.argv[1])
    else:
        db_file = Path(
            filedialog.askopenfilename(
                title="Select LU client SQLite DB",
                filetypes=[("SQLite DB", "*.db *.sqlite *.sqlite3"), ("All", "*.*")],
            )
        )
        if not db_file:
            print("No database selected - exiting.")
            return

    if not db_file.exists():
        print(f"Database not found: {db_file}")
        return

    app = Application(db_file)
    app.run()


if __name__ == "__main__":
    main()



"""
TODO:
- Create
   - duplicate existing item
   - add/remove components to existing item by right-clicking in component list
- Delete item
   - make common delete button code
- Scroll fields area will scroll page
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
"""

