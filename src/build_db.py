"""Build the Mini #20 lineage database from the SAMPLE CSVs.

Run:  python3 src/build_db.py
Writes: data/processed/lineage.db (rebuilt from scratch every run)
Reads:  data/raw/*_SAMPLE.csv + sql/schema.sql
Prints: row counts per table.

table_lineage is DERIVED here (distinct source -> target table pairs
from column_lineage) — it is not a separate CSV, because a table-level
edge with no column-level edge behind it would be a lie.
"""
import csv
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
DB = BASE / "data" / "processed" / "lineage.db"


def read_csv(name):
    with open(RAW / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build(db_path=DB):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript((BASE / "sql" / "schema.sql").read_text())
    counts = {}

    systems = read_csv("systems_SAMPLE.csv")
    con.executemany(
        "INSERT INTO systems VALUES (?, ?, ?, ?, ?)",
        [(r["system_id"], r["system_name"], r["system_type"],
          r["owner"], r["notes"]) for r in systems])
    counts["systems"] = len(systems)

    tables = read_csv("tables_SAMPLE.csv")
    con.executemany(
        "INSERT INTO tables VALUES (?, ?, ?, ?, ?)",
        [(int(r["table_id"]), r["table_name"], r["layer"],
          r["system_id"] or None, r["description"]) for r in tables])
    counts["tables"] = len(tables)
    table_id = {r["table_name"]: int(r["table_id"]) for r in tables}

    columns = read_csv("columns_SAMPLE.csv")
    con.executemany(
        "INSERT INTO columns VALUES (?, ?, ?, ?, ?, ?)",
        [(int(r["column_id"]), table_id[r["table_name"]],
          r["column_name"], r["data_type"], int(r["is_key"]),
          r["description"]) for r in columns])
    counts["columns"] = len(columns)
    column_id = {(r["table_name"], r["column_name"]): int(r["column_id"])
                 for r in columns}

    edges = read_csv("lineage_SAMPLE.csv")
    con.executemany(
        "INSERT INTO column_lineage VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(int(r["edge_id"]),
          table_id[r["source_table"]],
          column_id[(r["source_table"], r["source_column"])],
          table_id[r["target_table"]],
          column_id[(r["target_table"], r["target_column"])],
          r["transform_type"], r["transform_rule"]) for r in edges])
    counts["column_lineage"] = len(edges)

    # table_lineage: derived, one pair per distinct source->target table.
    pairs = sorted({(table_id[r["source_table"]],
                     table_id[r["target_table"]]) for r in edges})
    con.executemany("INSERT INTO table_lineage VALUES (?, ?)", pairs)
    counts["table_lineage"] = len(pairs)

    runs = read_csv("load_runs_SAMPLE.csv")
    con.executemany(
        "INSERT INTO load_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(r["run_id"], table_id[r["table_name"]], r["run_date"],
          r["started_at"], r["finished_at"], int(r["rows_loaded"]),
          int(r["rows_rejected"]), r["status"], r["notes"] or None)
         for r in runs])
    counts["load_runs"] = len(runs)

    reports = read_csv("reports_SAMPLE.csv")
    con.executemany(
        "INSERT INTO reports VALUES (?, ?, ?, ?)",
        [(r["report_id"], r["report_name"], r["owner"],
          r["refresh_cadence"]) for r in reports])
    counts["reports"] = len(reports)

    links = []
    for r in reports:
        for ref in r["uses_columns"].split(";"):
            tname, cname = ref.split(".", 1)
            links.append((r["report_id"], column_id[(tname, cname)]))
    con.executemany("INSERT INTO report_columns VALUES (?, ?)", links)
    counts["report_columns"] = len(links)

    con.commit()
    # Verify the DB agrees with the CSVs (belt and braces: the loader
    # must not silently drop a row).
    for table, expected in counts.items():
        got = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert got == expected, f"{table}: DB has {got}, CSV had {expected}"
    con.close()
    return counts


def main():
    counts = build()
    for table, n in counts.items():
        print(f"{table}: {n} rows")
    print(f"built {DB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
