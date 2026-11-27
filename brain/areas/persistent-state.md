# Where SQLite state survives a redeploy

Keep the database and its WAL sidecar files together on the persistent disk attached to the single Render service instance. WAL lets readers proceed during a write, but SQLite still serializes writers. For a quota reservation, exercise contention with synthetic requests and inspect the resulting ledger. The storage design alone cannot demonstrate atomic preflight or recovery after restart.

Sources: [A’s Render disk note](../../second-brain/3-resources/ingest/ingest_A_render-persistent-disks.md) and [A’s SQLite WAL note](../../second-brain/3-resources/ingest/ingest_A_sqlite-wal.md). Relevant to SRS §§6, 10 and TQ-6. See [[release-evidence]] for the verification record.
