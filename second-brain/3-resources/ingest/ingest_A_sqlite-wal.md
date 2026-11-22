# SQLite WAL Mode and Concurrent Writers

## Source

SQLite official documentation: [Write-Ahead Logging](https://www.sqlite.org/wal.html), [File Locking and Concurrency](https://www.sqlite.org/lockingv3.html), [When to Use SQLite](https://www.sqlite.org/whentouse.html)

## Ingested by / date

Person A · 2026-11-22

## Summary

SQLite's Write-Ahead Logging (WAL) mode is a journaling method that provides significant concurrency improvements over the default rollback journal. In WAL mode, readers do not block writers and writers do not block readers — reads and writes can proceed concurrently. However, SQLite still enforces a single-writer model: only one write transaction can be active at any time. Additional writers are serialized (they wait) rather than rejected. WAL mode works by appending changes to a separate WAL file instead of modifying the database file directly. Periodic checkpoints merge the WAL back into the main database. This architecture is well-suited for the project's deployment on Render with a single instance and persistent disk — the single-writer constraint aligns with the single-instance constraint of Render's persistent disks. The key risk is that WAL mode does not work over network filesystems, but since the database lives on a locally-mounted persistent disk, this is not an issue.

## Key facts

- WAL mode allows **concurrent reads and writes**: readers don't block writers and vice versa (source: SQLite WAL docs)
- SQLite enforces a **single-writer** model: only one write transaction at a time, additional writers wait (source: SQLite WAL docs)
- WAL mode is enabled per-connection with `PRAGMA journal_mode=WAL;` and persists on the database file (source: SQLite WAL docs)
- WAL files (`-wal`) and shared-memory files (`-shm`) are created alongside the database; both must be on the same filesystem (source: SQLite WAL docs)
- WAL mode does **not** work on network filesystems (NFS, SMB) — the database must be on a local or locally-mounted disk (source: SQLite WAL docs)
- Checkpointing merges WAL content back to the main database; automatic checkpointing happens by default after 1000 WAL pages (source: SQLite WAL docs)
- `busy_timeout` pragma sets how long a writer waits for the lock before returning `SQLITE_BUSY` (source: SQLite docs)
- WAL mode provides better performance for read-heavy workloads and workloads where reads and writes are interleaved (source: SQLite WAL docs)

## Relevance

- **ADR-02**: SQLite as the primary data store — WAL mode is the recommended journaling mode
- **SRS §6**: Deployment architecture with single Render instance and persistent disk
- **SRS §4**: Data management and storage requirements
- **ADR-07**: Deployment constraints — single-instance aligns with single-writer

## Open questions / risks

- What `busy_timeout` value should be set? Too low risks `SQLITE_BUSY` errors under load; too high risks request queueing.
- Checkpoint strategy: should the application trigger manual checkpoints, or rely on automatic checkpointing?
- If the application ever needs multiple writer processes (e.g. background workers), SQLite's single-writer model becomes a bottleneck. The current architecture (single Render instance) makes this acceptable.
- WAL file growth: if checkpointing doesn't keep up with writes, the WAL file can grow large. Monitor in production.
- Backup strategy: `sqlite3 .backup` or `VACUUM INTO` while WAL mode is active? Both are safe, but the approach should be documented.

## Links

- [[SQLite WAL Mode]]: https://www.sqlite.org/wal.html
- [[SQLite Locking]]: https://www.sqlite.org/lockingv3.html
- [[SQLite When to Use]]: https://www.sqlite.org/whentouse.html
- [[ADR-02 SQLite]]: docs/architecture/ (pending)
- [[Render Persistent Disks]]: https://docs.render.com/disks
