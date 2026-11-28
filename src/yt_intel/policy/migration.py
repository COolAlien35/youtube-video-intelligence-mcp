"""Idempotent SQLite migration for the Phase 3 event journal.

The Phase 2 policy_compliance_ledger contains determinations. Preserve its rows.
Phase 3 events reference determinations by identifier and have distinct semantics.
"""

from sqlalchemy.engine import Engine


def migrate(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql("""CREATE TABLE IF NOT EXISTS policy_subject_links (
            principal_key TEXT PRIMARY KEY NOT NULL, subject_ref TEXT UNIQUE NOT NULL)""")
        conn.exec_driver_sql("""CREATE TABLE IF NOT EXISTS policy_events (
            event_id INTEGER PRIMARY KEY, recorded_at TEXT NOT NULL, event TEXT NOT NULL,
            gate TEXT, subject_ref TEXT, evidence_ref TEXT)""")
        for verb in ("UPDATE", "DELETE"):
            conn.exec_driver_sql(f"""CREATE TRIGGER IF NOT EXISTS policy_events_no_{verb.lower()}
                BEFORE {verb} ON policy_events BEGIN
                SELECT RAISE(ABORT, 'append-only policy journal'); END""")
        conn.exec_driver_sql("""CREATE TRIGGER IF NOT EXISTS policy_events_no_replace
            BEFORE INSERT ON policy_events WHEN EXISTS(
            SELECT 1 FROM policy_events WHERE event_id=NEW.event_id)
            BEGIN SELECT RAISE(ABORT, 'append-only policy journal'); END""")
