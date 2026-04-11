from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from Domain.domains import Components, ObjectTypes
from Tests.helpers import connect_db, require_int_id


BASELINE_PATH = Path(__file__).with_name("BaseLine.sqlite")


@pytest.fixture(scope="session")
def baseline_path() -> Path:
    """Return the shared baseline SQLite database path.

    Args:
        None.

    Returns:
        Path: Existing path to the committed baseline database file.
    """
    if not BASELINE_PATH.is_file():
        pytest.skip(f"Missing baseline database: {BASELINE_PATH}")
    return BASELINE_PATH


@pytest.fixture()
def baseline_conn(baseline_path: Path):
    """Yield a read-only connection to the baseline SQLite database.

    Args:
        baseline_path: Path to the shared baseline SQLite database file.

    Yields:
        sqlite3.Connection: Connection configured with row access enabled.
    """
    conn = connect_db(baseline_path)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def temp_db_path(baseline_path: Path, tmp_path: Path) -> Path:
    """Create a per-test writable copy of the baseline SQLite database.

    Args:
        baseline_path: Path to the shared baseline SQLite database file.
        tmp_path: Pytest-provided temporary directory for the current test.

    Returns:
        Path: Filesystem path to the copied writable database.
    """
    db_path = tmp_path / "working.sqlite"
    shutil.copy2(baseline_path, db_path)
    return db_path


@pytest.fixture()
def item_with_components_id(baseline_conn) -> int:
    """Return an item object id that has both item and render components.

    Args:
        baseline_conn: Connection to the baseline SQLite database.

    Returns:
        int: Object id of a representative item record for load tests.
    """
    return require_int_id(
        baseline_conn,
        """
        SELECT o.id
        FROM Objects AS o
        JOIN ComponentsRegistry AS item_registry
            ON item_registry.id = o.id AND item_registry.component_type = ?
        JOIN ComponentsRegistry AS render_registry
            ON render_registry.id = o.id AND render_registry.component_type = ?
        WHERE o.type = ?
        ORDER BY o.id
        LIMIT 1
        """,
        (Components.ITEM, Components.RENDER, ObjectTypes.ITEM.value),
        "an item with ItemComponent and RenderComponent",
    )


@pytest.fixture()
def vendor_npc_id(baseline_conn) -> int:
    """Return an NPC object id that has a vendor component.

    Args:
        baseline_conn: Connection to the baseline SQLite database.

    Returns:
        int: Object id of a representative vendor NPC record.
    """
    return require_int_id(
        baseline_conn,
        """
        SELECT o.id
        FROM Objects AS o
        JOIN ComponentsRegistry AS vendor_registry
            ON vendor_registry.id = o.id AND vendor_registry.component_type = ?
        WHERE o.type IN (?, ?)
        ORDER BY o.id
        LIMIT 1
        """,
        (Components.VENDOR, ObjectTypes.NPC.value, ObjectTypes.NPC_2.value),
        "an NPC with VendorComponent",
    )
