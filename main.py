import sqlite3
import sys
from pathlib import Path
from tkinter import filedialog

from object import Object

def main():
    """Parse argv / open file dialog then launch Tk mainloop."""
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
            print("No database selected – exiting.")
            return

    if not db_file.exists():
        print(f"Database not found: {db_file}")
        return

    print(f"Opening database: {db_file}")
    # ---- SQLite connection ---------------------------------------
    # Keep open for lifetime of the app; row_factory → dict‑like rows.
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM Objects WHERE type = 'NPC'")

    rows = cur.fetchall()

    for row in rows:
        obj = Object(row['id'])
        obj.name = row['name']
        obj.placeable = row['placeable']
        obj.description = row['description']
        obj.type = row['type']
        obj.localize = row['localize']
        obj.npcTemplateID = row['npcTemplateID']
        obj.displayName = row['displayName']
        obj.interactionDistance = row['interactionDistance']
        obj.nametag = row['nametag']
        obj.internalNotes = row['_internalNotes']
        obj.locStatus = row['locStatus']
        obj.gate_version = row['gate_version']
        obj.hq_valid = row['hq_valid']

        obj.fetch_components(cur)

        print(f"Object ID: {obj.id}, Name: {obj.name}")




if __name__ == "__main__":
    main()
