from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable

import pytest


def connect_db(path: Path | str) -> sqlite3.Connection:
    """Open a SQLite connection configured like the repositories use.

    Args:
        path: Filesystem path to the SQLite database file.

    Returns:
        sqlite3.Connection: Open connection with row_factory and foreign keys enabled.
    """
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def count_rows(
    conn: sqlite3.Connection,
    table: str,
    where_sql: str = "1=1",
    params: Iterable[Any] = (),
) -> int:
    """Count rows in a table with an optional WHERE clause.

    Args:
        conn: Open SQLite connection used for the query.
        table: Table name to count rows from.
        where_sql: SQL fragment placed after WHERE.
        params: Positional values bound into the WHERE clause.

    Returns:
        int: Number of rows matching the supplied filter.
    """
    row = conn.execute(
        f"SELECT COUNT(*) AS row_count FROM {table} WHERE {where_sql}",
        tuple(params),
    ).fetchone()
    return int(row["row_count"])


def fetch_component_id(
    conn: sqlite3.Connection,
    object_id: int,
    component_type: int,
) -> int | None:
    """Look up a component id for an object/component-type pair.

    Args:
        conn: Open SQLite connection used for the query.
        object_id: Object id stored in ComponentsRegistry.id.
        component_type: Component type enum value stored in ComponentsRegistry.component_type.

    Returns:
        int | None: Matching component id, or None when no registry row exists.
    """
    row = conn.execute(
        """
        SELECT component_id
        FROM ComponentsRegistry
        WHERE id = ? AND component_type = ?
        """,
        (object_id, component_type),
    ).fetchone()
    return None if row is None else int(row["component_id"])


def fetch_component_types(conn: sqlite3.Connection, object_id: int) -> set[int]:
    """Return all component types registered for a given object.

    Args:
        conn: Open SQLite connection used for the query.
        object_id: Object id stored in ComponentsRegistry.id.

    Returns:
        set[int]: Component type values linked to the object.
    """
    rows = conn.execute(
        "SELECT component_type FROM ComponentsRegistry WHERE id = ?",
        (object_id,),
    ).fetchall()
    return {int(row["component_type"]) for row in rows}


def require_int_id(
    conn: sqlite3.Connection,
    query: str,
    params: Iterable[Any],
    label: str,
) -> int:
    """Run a query that must return a single integer id or skip the test.

    Args:
        conn: Open SQLite connection used for the query.
        query: SQL statement expected to return a row with an `id` column.
        params: Positional values bound into the SQL statement.
        label: Human-readable description used when skipping the test.

    Returns:
        int: The discovered id value from the query result.
    """
    row = conn.execute(query, tuple(params)).fetchone()
    if row is None:
        pytest.skip(f"Baseline DB does not contain {label}.")
    return int(row["id"])
