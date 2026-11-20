"""Connection pool and the per-request transaction.

Each request runs in one transaction as the least-privileged pharmatrace_app role. The first
statement records which staff member is acting, so database triggers can enforce roles and
write the audit log.
"""

from collections.abc import Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import get_settings

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(get_settings().app_url, min_size=1, max_size=10,
                               kwargs={"row_factory": dict_row}, open=True)
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def set_context(conn: psycopg.Connection, staff_id: int | None, reason: str | None = None) -> None:
    conn.execute("SELECT set_config('app.current_staff_id', %s, true), set_config('app.change_reason', %s, true)",
                 [str(staff_id) if staff_id else "", reason or ""])


def transaction(staff_id: int | None = None) -> Iterator[psycopg.Connection]:
    with get_pool().connection() as conn, conn.transaction():
        set_context(conn, staff_id)
        yield conn
