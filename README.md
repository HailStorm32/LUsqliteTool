
# LU Sqlite Tool



Desktop GUI for editing LEGO Universe SQLite client databases with focused workflows for `Items` and `NPCs`.



## End User Quick Start



If you only want to use the app, start here.



### 1. Download the App



- Open the [GitHub Releases page](https://github.com/HailStorm32/LUsqliteTool/releases)

- Download the latest binary for your platform

- Extract the download if the release asset is a `.zip`



### 2. Run the App



- Launch the downloaded executable

- When prompted, choose the SQLite database you want to edit, such as `cdclient.sqlite`



### 3. Make Your Changes



- Use the `Items` tab to create, duplicate, and edit item data

- Use the `NPCs` tab to create vendor or mission NPCs and edit related data

- Use the search box and sort controls in the left sidebar to find records quickly

- Select an object, component, or row in the tree to edit its fields on the right

- Right-click entries in the tree to add or remove supported components and rows

- Click `Save` when you are done



### 4. Safety Notes



- The app creates a `.bak` backup next to the selected database before editing

- If you close the app with unsaved changes, it will ask whether you want to save first



## Using the Tool



### Finding Records



- Search by ID or name from the left sidebar

- Sort by `id` or `name`

- Expand a record in the tree to inspect its components and child rows



### Editing Records



- Click the record you want to edit in the tree

- Update the fields in the form on the right

- Enable `Show advanced fields` if you need access to less common fields



### Creating and Duplicating



- Leave the ID field blank to auto-generate a new object ID

- Enter a positive integer if you want to control the new object ID yourself



Available creation actions:



-  `Items`: `Create`, `Duplicate`

-  `NPCs`: `Create Vendor`, `Create Mission`, `Duplicate`



### Deleting and Undoing Deletes



- Use the right-click context menu in the tree to delete supported objects, components, or rows

- Some deletes stay local until you save

- Use `Undo local deletes` to restore pending deletions before saving



## Development Setup



This section is for running the project from source.



### Requirements



- Python `3.11+`

-  `tkinter` available in your Python install



### Install Dependencies



Use the provided setup script from the project root.



#### Windows



```bat

setup-env.bat

```



#### macOS / Linux



```bash

./setup-env.sh

```



### Run From Source



After setup, run the app with the virtual environment's Python.



#### Windows



```powershell

.\.env\Scripts\python.exe main.py

```



#### macOS / Linux



```bash

./.env/bin/python  main.py

```



### Build With PyInstaller



The recommended build path is `build_pyinstaller.py`. It reads `APP_TITLE` and
`APP_ICON_PATH` from `main.py`, then passes the matching executable name,
bundled icon asset, and `.exe` icon settings to PyInstaller.



#### Windows



```powershell

.\.env\Scripts\python.exe build_pyinstaller.py

```



#### macOS / Linux



```bash

./.env/bin/python build_pyinstaller.py

```

### Optional Runtime Configuration



You can adjust these values at the top of `main.py`:



-  `DB_PATH`: preselect a database and skip the file picker

-  `LOG_LEVEL`: change logging verbosity

-  `LOG_DIR` and `LOG_FILE`: change log output location

-  `LOG_FILE_ONLY`: disable console logging

-  `APP_TITLE`: base window title shown in the title bar

-  `APP_VERSION`: version shown in the window title

-  `WINDOW_SIZE`: initial window size

-  `APP_ICON_PATH`: custom window icon path

Relative icon paths work from source and in bundled PyInstaller builds. The
default configuration uses `favicon.ico`. For a custom Windows title-bar
icon and packaged executable icon, point `APP_ICON_PATH` to a real `.ico` file.



### Logging



Logs are written to:



```text

logs/lusqlite_tool.log

```



### Project Layout



```text

.

|-- main.py

|-- gui/

|-- Service/

|-- Repository/

|-- Domain/

|-- requirements.txt

|-- setup-env.bat

|-- setup-env.sh

```



## Notes



- This tool edits live database content, so keep the generated `.bak` files until you have validated your changes

- This entire project is Codex generated. Human readability/maintainability was not a priority
