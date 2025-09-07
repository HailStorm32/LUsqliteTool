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
- Standardize _on_save method and place in base class
- Fix save for skills
- Add search functionality
   - search by ID
- Create
   - new item from scratch
   - duplicate existing item



"""