"""Ensure SQLite schema is migrated before API tests (stale app.db otherwise fails joins)."""

import pytest

from app.db.session import init_db


@pytest.fixture(scope="session", autouse=True)
def _init_sqlite_schema() -> None:
    init_db()
