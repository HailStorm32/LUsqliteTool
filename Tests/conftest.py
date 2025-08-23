"""Shared pytest fixtures for repository tests.

Provides:
- ro_conn: read-only connection to baseline DB (no mutations!)
- temp_db_path: path to a temp copy of baseline DB for mutation tests

Baseline file expected at Tests/BaseLine.sqlite.
"""
from __future__ import annotations
import os
import shutil
import sqlite3
import pytest

BASELINE = os.path.join(os.path.dirname(__file__), 'BaseLine.sqlite')

@pytest.fixture(scope='session')
def _baseline_present():
    if not os.path.isfile(BASELINE):
        pytest.skip('Missing Tests/BaseLine.sqlite baseline database')

@pytest.fixture()
def ro_conn(_baseline_present):
    conn = sqlite3.connect(BASELINE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        yield conn
    finally:
        conn.close()

@pytest.fixture(scope='session')
def baseline_path(_baseline_present) -> str:
    """Provide the filesystem path to the baseline database."""
    return BASELINE

@pytest.fixture()
def temp_db_path(_baseline_present, tmp_path) -> str:
    dst = tmp_path / 'working.sqlite'
    shutil.copyfile(BASELINE, dst)
    return str(dst)
