"""
vasrd_schema.py
SQLite schema helper for the VASRD Toolkit.
"""

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS body_systems (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    cfr_section   TEXT,
    notes         TEXT
);

CREATE TABLE IF NOT EXISTS diagnostic_codes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    dc_code        INTEGER NOT NULL,
    name           TEXT    NOT NULL,
    body_system_id INTEGER,
    cfr_section    TEXT,
    notes          TEXT,
    UNIQUE(dc_code),
    FOREIGN KEY(body_system_id) REFERENCES body_systems(id)
);

CREATE TABLE IF NOT EXISTS rating_criteria (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    dc_id          INTEGER,
    percentage     INTEGER NOT NULL,
    criteria_text  TEXT    NOT NULL,
    FOREIGN KEY(dc_id) REFERENCES diagnostic_codes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dc_notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    dc_id       INTEGER NOT NULL,
    note_number INTEGER,
    note_text   TEXT    NOT NULL,
    FOREIGN KEY(dc_id) REFERENCES diagnostic_codes(id) ON DELETE CASCADE
);
"""

def create_schema(conn):
    """Create/verify all tables."""
    conn.executescript(SCHEMA)
    conn.commit()
