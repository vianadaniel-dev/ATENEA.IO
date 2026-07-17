"""Connection to PostgreSQL (Supabase) using a Psycopg connection pool.

This module contains only:
  * pool creation,
  * functions to obtain a connection,
  * functions to release the connection,
  * basic connection error handling.

It does not contain business logic or domain SQL queries.
"""

import logging
import threading
from contextlib import contextmanager
from typing import Iterator, Optional

import psycopg2
from psycopg2 import OperationalError
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from config import settings

logger = logging.getLogger(__name__)


class DatabaseError(RuntimeError):
    """Infrastructure error when connecting or operating against the database."""


_pool: Optional[ThreadedConnectionPool] = None
_pool_lock = threading.Lock()


def init_pool() -> ThreadedConnectionPool:
    """Creates the connection pool if it does not exist yet and returns it.

    It is idempotent and thread-safe: multiple concurrent requests
    can call it without creating duplicate pools.
    """
    global _pool
    if _pool is not None:
        return _pool

    with _pool_lock:
        # Second check: another thread may have created it while we waited.
        if _pool is not None:
            return _pool
        try:
            _pool = ThreadedConnectionPool(
                minconn=settings.DB_POOL_MIN,
                maxconn=settings.DB_POOL_MAX,
                dsn=settings.DATABASE_URL,
                sslmode=settings.DB_SSLMODE,
                connect_timeout=settings.DB_CONNECT_TIMEOUT,
                cursor_factory=RealDictCursor,
            )
        except OperationalError as exc:
            raise DatabaseError(
                "Could not create the connection pool. Verify DATABASE_URL "
                f"and that the database accepts connections. Detail: {exc}"
            ) from exc

        logger.info(
            "Connection pool created (min=%s, max=%s, sslmode=%s)",
            settings.DB_POOL_MIN,
            settings.DB_POOL_MAX,
            settings.DB_SSLMODE,
        )
        return _pool


def get_pool() -> ThreadedConnectionPool:
    """Returns the pool, creating it on the first call."""
    return init_pool()


def close_pool() -> None:
    """Closes all pool connections. Use when shutting down the application."""
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.closeall()
            _pool = None
            logger.info("Connection pool closed")


def acquire_connection() -> PgConnection:
    """Borrows a connection from the pool."""
    pool = get_pool()
    try:
        return pool.getconn()
    except (OperationalError, psycopg2.PoolError) as exc:
        raise DatabaseError(f"Could not get a connection from the pool: {exc}") from exc


def release_connection(conn: Optional[PgConnection], close: bool = False) -> None:
    """Returns the connection to the pool. Never raises exceptions."""
    if conn is None:
        return
    try:
        get_pool().putconn(conn, close=close)
    except Exception:  # noqa: BLE001 - releasing must never break the request
        logger.exception("Error returning the connection to the pool")


@contextmanager
def get_connection() -> Iterator[PgConnection]:
    """Context manager that guarantees the connection is always released.

    If the connection breaks it is discarded instead of returned to the pool,
    to avoid reusing a broken connection.
    """
    conn: Optional[PgConnection] = None
    discard = False
    try:
        conn = acquire_connection()
        yield conn
    except OperationalError as exc:
        discard = True
        raise DatabaseError(f"Lost connection to the database: {exc}") from exc
    finally:
        release_connection(conn, close=discard)


@contextmanager
def get_cursor(conn: PgConnection) -> Iterator[RealDictCursor]:
    """Opens a cursor that returns rows as dictionaries."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        yield cur


def get_db() -> Iterator[PgConnection]:
    """FastAPI dependency: provides a transactional connection.

    Commits if the endpoint finishes successfully and rollbacks if an exception occurs.
    """
    with get_connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def check_connection() -> bool:
    """Checks that the database responds. Useful for a healthcheck."""
    try:
        with get_connection() as conn, get_cursor(conn) as cur:
            cur.execute("SELECT 1 AS ok")
            return cur.fetchone() is not None
    except DatabaseError:
        logger.exception("Database healthcheck failed")
        return False
