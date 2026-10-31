"""Storage: SQLite for laptops and tests, Postgres for production. One dialect in the code, two engines underneath.

  DATABASE_URL=postgres://...   -> Postgres (psycopg 3), autocommit, statements translated from the SQLite dialect
  otherwise                     -> SQLite file (SUBSTRATE_DB) or :memory:

Translation covers exactly what Substrate uses: ? placeholders, INSERT OR REPLACE (as ON CONFLICT upserts on the
table's key), AUTOINCREMENT, ROWID ordering, PRAGMA. Every table gets the same schema in both engines.

Chain safety across many servers: events carry a UNIQUE (user_id, prev_hash) index, so two concurrent appends to
the same person's ledger cannot both succeed; the loser re-reads the head and retries (see Store.append).
"""
from __future__ import annotations

import os
import re
import sqlite3
import threading

# table -> (conflict key, all columns in order) for INSERT OR REPLACE translation
UPSERT = {
    "persons": ("user_id", ["user_id", "body"]),
    "owners": ("user_id", ["user_id", "tenant_id"]),
    "letters": ("id", ["id", "to_user", "from_user", "body"]),
    "webhooks": ("tenant_id", ["tenant_id", "url", "secret", "events", "created"]),
    "accounts": ("email", ["email", "user_id", "pw", "created", "failed", "locked_until"]),
}
_INSERT_OR_REPLACE = re.compile(r"insert\s+or\s+replace\s+into\s+(\w+)\s+values\s*\(([^)]*)\)", re.I)


def is_postgres_url(url: str | None) -> bool:
    return bool(url) and url.split(":", 1)[0] in ("postgres", "postgresql")


def translate(sql: str) -> str:
    s = sql
    m = _INSERT_OR_REPLACE.search(s)
    if m:
        table, vals = m.group(1), m.group(2)
        key, cols = UPSERT[table]
        n = vals.count("?")
        cols = cols[:n]
        sets = ", ".join(f"{c}=excluded.{c}" for c in cols if c != key)
        s = f"insert into {table} ({', '.join(cols)}) values ({vals}) on conflict ({key}) do update set {sets}"
    s = re.sub(r"integer\s+primary\s+key\s+autoincrement", "bigserial primary key", s, flags=re.I)
    s = re.sub(r"order\s+by\s+rowid", "order by seq", s, flags=re.I)
    return s.replace("?", "%s")


class _PGCursor:
    def __init__(self, cur):
        self._c = cur

    def fetchone(self):
        return self._c.fetchone() if self._c.description else None

    def fetchall(self):
        return self._c.fetchall() if self._c.description else []

    def __iter__(self):
        return iter(self.fetchall())

    @property
    def rowcount(self):
        return self._c.rowcount


class PG:
    """Just enough of the sqlite3.Connection surface for Substrate, on Postgres."""
    kind = "postgres"

    def __init__(self, url: str):
        import psycopg
        self._psycopg = psycopg
        self.conn = psycopg.connect(url, autocommit=True)
        self._lock = threading.RLock()

    def execute(self, sql: str, params=()):
        if sql.strip().lower().startswith("pragma"):
            return _PGCursor(self.conn.cursor())
        with self._lock:
            cur = self.conn.cursor()
            try:
                cur.execute(translate(sql), tuple(params))
            except self._psycopg.errors.UniqueViolation as e:
                raise sqlite3.IntegrityError(str(e)) from None
            return _PGCursor(cur)

    def executescript(self, script: str):
        for stmt in [x.strip() for x in script.split(";") if x.strip()]:
            self.execute(stmt)

    def commit(self):
        pass   # autocommit

    def close(self):
        self.conn.close()


class SQLite:
    """sqlite3 with one lock: FastAPI runs sync endpoints on a thread pool, and the console fires many requests
    at once. Without this, a laptop demo answers some of them with 'bad parameter or other API misuse'."""
    kind = "sqlite"

    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.RLock()

    def execute(self, sql: str, params=()):
        with self._lock:
            return self.conn.execute(sql, params)

    def executescript(self, script: str):
        with self._lock:
            return self.conn.executescript(script)

    def commit(self):
        with self._lock:
            self.conn.commit()

    def close(self):
        self.conn.close()


def connect(path: str | None):
    url = os.environ.get("DATABASE_URL")
    if path is None and is_postgres_url(url):
        return PG(url)
    return SQLite(path or os.environ.get("SUBSTRATE_DB", "substrate.db"))
