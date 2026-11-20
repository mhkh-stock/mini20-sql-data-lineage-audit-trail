"""Rebuild lineage.db and run all 10 Mini #20 queries.

Run:  python3 src/run_queries.py
Writes: data/processed/lineage.db, outputs/query_NN_<slug>.csv (one per
        query, header row included).
Prints: one line per query with its row count.

Requires Python 3 + SQLite (standard library only).
"""
import csv
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "src"))

import build_db  # noqa: E402

QUERIES = [
    ("01", "upstream_lineage_net_revenue"),
    ("02", "downstream_impact_unit_price"),
    ("03", "orphan_columns"),
    ("04", "tables_without_reports"),
    ("05", "load_run_audit"),
    ("06", "table_freshness"),
    ("07", "transform_inventory"),
    ("08", "report_dependency_map"),
    ("09", "lineage_completeness"),
    ("10", "change_request_cost_price"),
]


def main():
    build_db.build()
    (BASE / "outputs").mkdir(exist_ok=True)
    con = sqlite3.connect(BASE / "data" / "processed" / "lineage.db")
    results = {}
    for num, slug in QUERIES:
        path = BASE / "sql" / f"{num}_{slug}.sql"
        cur = con.execute(path.read_text())
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        results[num] = (cols, rows)
        out = BASE / "outputs" / f"query_{num}_{slug}.csv"
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)
        print(f"ran {path.name}: {len(rows)} rows -> {out.name}")
    con.close()
    return results


if __name__ == "__main__":
    main()
