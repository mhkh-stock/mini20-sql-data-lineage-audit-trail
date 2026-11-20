-- Mini #20 — SQL Data Lineage & Audit Trail Pack
-- SAMPLE / DEMO data only. Fictional shop (Noor Electronics), fictional
-- systems, fictional numbers. Never claimed as real client or real
-- business data. SQLite 3.30+.
-- The database is built by src/build_db.py from data/raw/*.csv.
-- table_lineage is DERIVED in build_db.py (distinct source -> target
-- table pairs from column_lineage) — it is not a separate CSV, because
-- a table-level edge that has no column-level edge behind it would be
-- a lie. Every table edge here is backed by at least one column edge.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS report_columns;
DROP TABLE IF EXISTS reports;
DROP TABLE IF EXISTS load_runs;
DROP TABLE IF EXISTS table_lineage;
DROP TABLE IF EXISTS column_lineage;
DROP TABLE IF EXISTS columns;
DROP TABLE IF EXISTS tables;
DROP TABLE IF EXISTS systems;

CREATE TABLE systems (
    system_id   TEXT PRIMARY KEY,
    system_name TEXT NOT NULL,
    system_type TEXT NOT NULL,
    owner       TEXT NOT NULL,
    notes       TEXT
);

CREATE TABLE tables (
    table_id    INTEGER PRIMARY KEY,
    table_name  TEXT NOT NULL UNIQUE,
    layer       TEXT NOT NULL CHECK (layer IN ('staging', 'warehouse')),
    system_id   TEXT REFERENCES systems (system_id),
    description TEXT
);

CREATE TABLE columns (
    column_id   INTEGER PRIMARY KEY,
    table_id    INTEGER NOT NULL REFERENCES tables (table_id),
    column_name TEXT NOT NULL,
    data_type   TEXT NOT NULL,
    is_key      INTEGER NOT NULL CHECK (is_key IN (0, 1)),
    description TEXT,
    UNIQUE (table_id, column_name)
);

CREATE TABLE column_lineage (
    edge_id          INTEGER PRIMARY KEY,
    source_table_id  INTEGER NOT NULL REFERENCES tables (table_id),
    source_column_id INTEGER NOT NULL REFERENCES columns (column_id),
    target_table_id  INTEGER NOT NULL REFERENCES tables (table_id),
    target_column_id INTEGER NOT NULL REFERENCES columns (column_id),
    transform_type   TEXT NOT NULL CHECK (transform_type IN ('pass-through', 'calculated')),
    transform_rule   TEXT NOT NULL
);

CREATE TABLE table_lineage (
    source_table_id INTEGER NOT NULL REFERENCES tables (table_id),
    target_table_id INTEGER NOT NULL REFERENCES tables (table_id),
    PRIMARY KEY (source_table_id, target_table_id)
);

CREATE TABLE load_runs (
    run_id       TEXT PRIMARY KEY,
    table_id     INTEGER NOT NULL REFERENCES tables (table_id),
    run_date     TEXT NOT NULL,  -- ISO date YYYY-MM-DD
    started_at   TEXT NOT NULL,  -- HH:MM
    finished_at  TEXT NOT NULL,  -- HH:MM
    rows_loaded  INTEGER NOT NULL CHECK (rows_loaded >= 0),
    rows_rejected INTEGER NOT NULL CHECK (rows_rejected >= 0),
    status       TEXT NOT NULL CHECK (status IN ('success', 'failed', 'partial')),
    notes        TEXT
);

CREATE TABLE reports (
    report_id       TEXT PRIMARY KEY,
    report_name     TEXT NOT NULL,
    owner           TEXT NOT NULL,
    refresh_cadence TEXT NOT NULL
);

CREATE TABLE report_columns (
    report_id TEXT NOT NULL REFERENCES reports (report_id),
    column_id INTEGER NOT NULL REFERENCES columns (column_id),
    PRIMARY KEY (report_id, column_id)
);
