# Ingest: SQLAlchemy 2.x with SQLite — WAL, BEGIN IMMEDIATE, and pysqlite caveats

## Source

- **Primary:** SQLAlchemy 2.x documentation — SQLite dialect
  <https://docs.sqlalchemy.org/en/20/dialects/sqlite.html>
- **Section:** "Serializable isolation / Savepoints / Transactional DDL"
  <https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#serializable-isolation-savepoints-transactional-ddl>
- **Section:** "pysqlite" (default DBAPI)
  <https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#pysqlite>

## Ingested by / Date

Person A (Pulkit) · 2026-11-27

## Summary

SQLAlchemy's default DBAPI for SQLite is `pysqlite` (Python's built-in
`sqlite3` module). pysqlite has non-standard transaction-control behaviour
that breaks `BEGIN IMMEDIATE` semantics when you rely on SQLAlchemy's
normal `engine.begin()` context manager. This note documents the caveats
and the explicit workaround implemented in `src/yt_intel/quota/service.py`.

## Key Facts

### 1. pysqlite emits `BEGIN` (deferred) by default, not `BEGIN IMMEDIATE`

**Source:** SQLAlchemy docs — "Serializable isolation / Savepoints" section.

When SQLAlchemy calls `engine.begin()`, the underlying pysqlite DBAPI
issues a plain `BEGIN` statement (SQLite's *deferred* transaction mode).
In deferred mode, the database does not acquire any lock until the first
read or write. This means two concurrent writers can both pass a read-then-
write check before either has committed, causing a lost-update race.

For the quota ledger (which does `SELECT … then UPDATE …` atomically),
*deferred* mode is insufficient.

### 2. `BEGIN IMMEDIATE` must be issued explicitly

**Source:** SQLAlchemy docs — same section; pysqlite workaround examples.

`BEGIN IMMEDIATE` acquires a *reserved* lock at the start of the
transaction. Any concurrent `BEGIN IMMEDIATE` by another connection will
block (up to `busy_timeout`) rather than racing past the lock.

Because pysqlite intercepts and suppresses any `BEGIN` statement that
SQLAlchemy tries to send (it manages its own implicit transactions),
the only reliable way to get `BEGIN IMMEDIATE` is to issue it explicitly
*inside* an already-open `engine.begin()` block:

```python
with engine.begin() as conn:
    conn.execute(text("BEGIN IMMEDIATE"))
    # now all reads and writes in this block are under IMMEDIATE lock
    row = conn.execute(text("SELECT ...")).fetchone()
    conn.execute(text("UPDATE ..."))
# COMMIT happens automatically on context-manager exit
```

This pattern is used in `QuotaService.reserve()`, `QuotaService.settle()`,
and `QuotaService.release()`.

### 3. `check_same_thread=False` is required for multi-threaded use

**Source:** pysqlite documentation; SQLAlchemy SQLite dialect notes.

By default, SQLite's pysqlite DBAPI raises an error if the same connection
is used from a thread other than the one that created it. When a connection
pool is used (SQLAlchemy's default), connections are handed to whichever
thread calls `engine.connect()` or `engine.begin()`. The flag must be
passed via `connect_args`:

```python
create_engine(
    "sqlite:///path/to/db.sqlite",
    connect_args={"check_same_thread": False},
)
```

This is set in `src/yt_intel/storage/db.py::get_engine()`.

### 4. WAL mode and `synchronous=NORMAL` must be set via event listener

**Source:** SQLAlchemy docs — "SQLite-specific PRAGMA" section.

PRAGMA statements must be emitted on **each new connection**, not once at
engine creation time (since they are connection-scoped, not database-scoped
in SQLite). SQLAlchemy's `@event.listens_for(engine, "connect")` hook is
the correct place:

```python
@event.listens_for(engine, "connect")
def _configure_sqlite(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA journal_mode=WAL")
    dbapi_conn.execute("PRAGMA foreign_keys=ON")
    dbapi_conn.execute("PRAGMA busy_timeout=5000")
    dbapi_conn.execute("PRAGMA synchronous=NORMAL")
```

`synchronous=NORMAL` is safe with WAL mode; it provides durability on most
OS crash scenarios while being significantly faster than `FULL`.

### 5. SQLAlchemy 2.x API (`future=True` / 2.x engine)

**Source:** SQLAlchemy 2.x migration guide.

In SQLAlchemy 2.x, `create_engine()` already returns a 2.x-style engine
(the `future=True` flag from 1.4 is no longer needed and is ignored).
The 2.x engine uses `Connection.execute()` returning `CursorResult`, not
the legacy `ResultProxy`. All code in this repo targets SQLAlchemy ≥2.0 and
uses the 2.x API directly.

### 6. `busy_timeout` prevents `OperationalError: database is locked`

**Source:** SQLite documentation; SQLAlchemy dialect notes.

Without a busy timeout, a second writer hitting an already-locked database
immediately raises `sqlite3.OperationalError: database is locked`. Setting
`PRAGMA busy_timeout=5000` tells SQLite to retry for up to 5 seconds before
raising. This is appropriate for local single-node deployments; distributed
workloads should use Postgres instead.

## Relevance

| SRS ID | Description |
|--------|-------------|
| TQ-5   | Atomic dual-bucket quota check |
| TQ-6   | Quota ledger persisted in SQLite WAL |
| TQ-7   | Concurrent reservation safety |
| TQ-8   | Quota reset at Pacific midnight |
| NFR-04 | No data loss on crash (WAL + synchronous=NORMAL) |
| NFR-05 | Quota service must be synchronous (async callers use anyio.to_thread) |
| DATA-01 | Storage layer uses SQLite for Phase 2 |

## Open Questions / Risks

| # | Question / Risk | Status |
|---|----------------|--------|
| 1 | `BEGIN IMMEDIATE` inside `engine.begin()` works on pysqlite but may behave differently with other SQLite drivers (e.g., `aiosqlite`). We use sync-only; risk is low. | ⊘ Acceptable for Phase 2 |
| 2 | WAL mode is per-database-file. If the data directory contains multiple `.sqlite` files, each must be individually WAL-enabled. Currently only one file (`yt_intel.db`). | ⊘ Noted, single-file for now |
| 3 | `busy_timeout=5000` (5 s) may be too long for a web request handler. If a lock is held for >5 s the HTTP request will time out before the DB error. Consider reducing to 2–3 s in Phase 3. | ⚠️ Revisit in Phase 3 |
| 4 | Phase 3 decision: Alembic vs `metadata.create_all()`. WAL pragma must still be set via the event listener even with Alembic (Alembic does not set PRAGMAs for you). | 🔲 Open (tracked in GitHub issue) |

## Links

- SQLAlchemy SQLite dialect: <https://docs.sqlalchemy.org/en/20/dialects/sqlite.html>
- pysqlite DBAPI: <https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#pysqlite>
- Serializable isolation workaround: <https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#serializable-isolation-savepoints-transactional-ddl>
- SQLite WAL mode: <https://www.sqlite.org/wal.html>
- SQLite locking and concurrency: <https://www.sqlite.org/lockingv3.html>
- Implementation: [`src/yt_intel/storage/db.py`](../../src/yt_intel/storage/db.py)
- Implementation: [`src/yt_intel/quota/service.py`](../../src/yt_intel/quota/service.py)
