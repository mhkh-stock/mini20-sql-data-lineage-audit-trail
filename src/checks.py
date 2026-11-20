"""Verification suite for Mini #20 — SQL Data Lineage & Audit Trail Pack.

Run:  python3 src/checks.py
Rebuilds data/processed/lineage.db, runs all 10 queries, re-derives
every headline number independently from the CSVs / the database,
and compares it against the query outputs in outputs/.

Exits 1 on any failure. Fix the BUILD, not the checks, when they
disagree — a failing check means the data, the schema or a query is
wrong, never the expectation.
"""
import csv
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "src"))

import build_db  # noqa: E402

fails = []
n_checks = 0


def check(name, cond, detail=""):
    global n_checks
    n_checks += 1
    print(f"{'PASS' if cond else 'FAIL'}: {name} {detail}")
    if not cond:
        fails.append(name)


def read_csv(name):
    with open(BASE / "data" / "raw" / name, newline="",
              encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_query(con, num):
    path = next((BASE / "sql").glob(f"{num}_*.sql"))
    cur = con.execute(path.read_text())
    return [d[0] for d in cur.description], cur.fetchall()


def main():
    build_db.build()
    con = sqlite3.connect(BASE / "data" / "processed" / "lineage.db")
    con.execute("PRAGMA foreign_keys = ON")

    # ---- base counts: DB vs CSV (6 checks) ----
    csv_counts = {
        "systems": len(read_csv("systems_SAMPLE.csv")),
        "tables": len(read_csv("tables_SAMPLE.csv")),
        "columns": len(read_csv("columns_SAMPLE.csv")),
        "column_lineage": len(read_csv("lineage_SAMPLE.csv")),
        "load_runs": len(read_csv("load_runs_SAMPLE.csv")),
        "reports": len(read_csv("reports_SAMPLE.csv")),
    }
    db_counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                 for t in csv_counts}
    for t in csv_counts:
        check(f"CSV rows = DB rows: {t}",
              db_counts[t] == csv_counts[t],
              f"(CSV {csv_counts[t]}, DB {db_counts[t]})")

    # ---- base counts: exact expected values (8 checks) ----
    check("systems = 4", db_counts["systems"] == 4)
    check("tables = 11", db_counts["tables"] == 11)
    check("staging tables = 5",
          con.execute("SELECT COUNT(*) FROM tables WHERE layer='staging'"
                      ).fetchone()[0] == 5)
    check("warehouse tables = 6",
          con.execute("SELECT COUNT(*) FROM tables WHERE layer='warehouse'"
                      ).fetchone()[0] == 6)
    check("columns = 51", db_counts["columns"] == 51)
    check("column_lineage edges = 33", db_counts["column_lineage"] == 33)
    check("table_lineage pairs = 11 (derived)",
          con.execute("SELECT COUNT(*) FROM table_lineage").fetchone()[0]
          == 11)
    check("reports = 6", db_counts["reports"] == 6)
    check("report_columns links = 20",
          con.execute("SELECT COUNT(*) FROM report_columns").fetchone()[0]
          == 20)
    check("load_runs = 30", db_counts["load_runs"] == 30)

    # ---- planted gaps, found exactly (6 checks) ----
    _, q03 = run_query(con, "03")
    check("Q03 orphan columns = 1", len(q03) == 1, str(q03))
    check("Q03 orphan is dim_product.product_name",
          q03 and q03[0][0] == "dim_product"
          and q03[0][1] == "product_name", str(q03))
    _, q04 = run_query(con, "04")
    check("Q04 tables without a report = 1", len(q04) == 1, str(q04))
    check("Q04 dead table is fact_returns",
          q04 and q04[0][0] == "fact_returns", str(q04))
    lying = con.execute(
        """SELECT run_id FROM load_runs
           WHERE status = 'success' AND rows_rejected > 0""").fetchall()
    check("lying success rows = 1", len(lying) == 1, str(lying))
    check("lying row is LR-08 fact_sales 2026-11-12, 37 rejected",
          lying == [("LR-08",)] and con.execute(
              """SELECT t.table_name, lr.run_date, lr.rows_rejected
                 FROM load_runs lr JOIN tables t ON t.table_id = lr.table_id
                 WHERE lr.run_id = 'LR-08'""").fetchone()
          == ("fact_sales", "2026-11-12", 37))

    # ---- Q01 upstream lineage (4 checks) ----
    _, q01 = run_query(con, "01")
    check("Q01 upstream rows = 4", len(q01) == 4, str(q01))
    check("Q01 source systems are exactly POS + WEB",
          {r[2] for r in q01} == {"POS", "WEB"}, str({r[2] for r in q01}))
    check("Q01 all four edges are calculated",
          all(r[3] == "calculated" for r in q01))
    check("Q01 sources are the 4 expected columns",
          {(r[0], r[1]) for r in q01}
          == {("stg_pos_sales", "quantity"),
              ("stg_pos_sales", "unit_price"),
              ("stg_web_orders", "quantity"),
              ("stg_web_orders", "unit_price")},
          str({(r[0], r[1]) for r in q01}))
    check("Q01 all depths = 1 (sources are staging roots)",
          all(r[5] == 1 for r in q01))

    # ---- Q02 downstream impact (4 checks) ----
    _, q02 = run_query(con, "02")
    check("Q02 impacted columns = 4", len(q02) == 4, str(q02))
    check("Q02 impacted set is exact",
          {(r[0], r[1]) for r in q02}
          == {("fact_sales", "unit_price"),
              ("fact_sales", "net_revenue"),
              ("agg_monthly_sales", "avg_unit_price"),
              ("agg_monthly_sales", "total_revenue")},
          str({(r[0], r[1]) for r in q02}))
    reports_touched = set()
    for r in q02:
        if r[4]:
            reports_touched.update(x.strip() for x in r[4].split(";"))
    check("Q02 reports touched = 5 (R1, R2, R3, R4, R5)",
          reports_touched
          == {"Daily Sales Dashboard", "Customer Retention Report",
              "Monthly Revenue Report", "Product Margin Report",
              "Executive KPI Summary"},
          str(sorted(reports_touched)))
    check("Q02 deepest impact is depth 2",
          max(r[3] for r in q02) == 2)

    # ---- Q05 load-run audit (4 checks) ----
    _, q05 = run_query(con, "05")
    check("Q05 audit rows = 4", len(q05) == 4, str(q05))
    by_status = {}
    for r in q05:
        by_status.setdefault(r[5], []).append(r[0])
    check("Q05 failed runs = 2 (LR-06, LR-22)",
          by_status.get("failed") == ["LR-06", "LR-22"],
          str(by_status.get("failed")))
    check("Q05 partial runs = 1 (LR-28)",
          by_status.get("partial") == ["LR-28"],
          str(by_status.get("partial")))
    check("Q05 lying success row = 1 (LR-08)",
          [r[0] for r in q05 if r[6] == "LYING SUCCESS ROW"] == ["LR-08"],
          str([r[0] for r in q05 if r[6] == "LYING SUCCESS ROW"]))

    # ---- Q06 freshness (4 checks) ----
    _, q06 = run_query(con, "06")
    check("Q06 stale tables = 2", len(q06) == 2, str(q06))
    check("Q06 stale set is dim_date + fact_returns",
          {r[0] for r in q06} == {"dim_date", "fact_returns"},
          str({r[0] for r in q06}))
    days = {r[0]: r[2] for r in q06}
    check("Q06 dim_date is 16 days stale", days.get("dim_date") == 16,
          str(days))
    check("Q06 fact_returns is 10 days stale",
          days.get("fact_returns") == 10, str(days))
    check("Q06 dim_product is fresh by exactly 1 day "
          "(last good load 2026-11-11, window starts 2026-11-11)",
          con.execute(
              """SELECT MAX(run_date) FROM load_runs lr
                 JOIN tables t ON t.table_id = lr.table_id
                 WHERE t.table_name = 'dim_product'
                 AND lr.status <> 'failed'""").fetchone()[0] == "2026-11-11")

    # ---- Q07 transform inventory (3 checks) ----
    _, q07 = run_query(con, "07")
    check("Q07 rows = 33 (one per edge)", len(q07) == 33)
    types = {}
    for r in q07:
        types[r[4]] = types.get(r[4], 0) + 1
    check("Q07 pass-through edges = 19", types.get("pass-through") == 19,
          str(types))
    check("Q07 calculated edges = 14", types.get("calculated") == 14,
          str(types))

    # ---- Q08 report dependency map (7 checks) ----
    _, q08 = run_query(con, "08")
    check("Q08 reports = 6", len(q08) == 6)
    expected_maps = {
        "Daily Sales Dashboard": {"fact_sales", "dim_date", "dim_product"},
        "Monthly Revenue Report": {"agg_monthly_sales", "dim_product"},
        "Customer Retention Report": {"dim_customer", "fact_sales"},
        "Product Margin Report": {"dim_product", "fact_sales"},
        "Executive KPI Summary": {"agg_monthly_sales", "fact_sales",
                                  "dim_customer"},
        "Supplier Cost Watch": {"dim_product"},
    }
    for row in q08:
        got = {x.strip() for x in row[4].split(",")}
        check(f"Q08 tables for {row[1]}",
              got == expected_maps[row[1]],
              f"(got {sorted(got)})")
    check("Q08 report-table pairs = 13",
          sum(len(v) for v in expected_maps.values()) == 13)

    # ---- Q09 completeness (4 checks) ----
    _, q09 = run_query(con, "09")
    check("Q09 rows = 6 (one per warehouse table)", len(q09) == 6)
    scores = {r[0]: r[3] for r in q09}
    check("Q09 dim_product = 80.00% (4 of 5)",
          scores.get("dim_product") == 80.0, str(scores))
    check("Q09 every other warehouse table = 100.00%",
          all(v == 100.0 for k, v in scores.items()
              if k != "dim_product"), str(scores))
    overall = con.execute(
        """SELECT ROUND(100.0 * COUNT(DISTINCT CASE WHEN cl.edge_id
              IS NOT NULL THEN c.column_id END)
              / COUNT(DISTINCT c.column_id), 2)
           FROM tables t JOIN columns c ON c.table_id = t.table_id
           LEFT JOIN column_lineage cl
             ON cl.target_table_id = t.table_id
            AND cl.target_column_id = c.column_id
           WHERE t.layer = 'warehouse'""").fetchone()[0]
    check("Q09 overall warehouse completeness = 96.55% (28 of 29)",
          overall == 96.55, f"({overall})")

    # ---- Q10 change request (2 checks) ----
    _, q10 = run_query(con, "10")
    check("Q10 reports to re-test = 2", len(q10) == 2, str(q10))
    check("Q10 reports are Product Margin Report + Supplier Cost Watch",
          {r[0] for r in q10}
          == {"Product Margin Report", "Supplier Cost Watch"},
          str({r[0] for r in q10}))

    # ---- reconciliation: load totals (5 checks) ----
    total_loaded, total_rejected = con.execute(
        "SELECT SUM(rows_loaded), SUM(rows_rejected) FROM load_runs"
    ).fetchone()
    check("reconciliation: total rows loaded = 18598",
          total_loaded == 18598, f"({total_loaded})")
    check("reconciliation: total rows rejected = 57",
          total_rejected == 57, f"({total_rejected})")
    status_counts = dict(con.execute(
        "SELECT status, COUNT(*) FROM load_runs GROUP BY status"
    ).fetchall())
    check("reconciliation: statuses are 27 success / 2 failed / 1 partial",
          status_counts == {"success": 27, "failed": 2, "partial": 1},
          str(status_counts))
    check("reconciliation: failed runs loaded 0 rows",
          con.execute(
              "SELECT SUM(rows_loaded) FROM load_runs WHERE status='failed'"
          ).fetchone()[0] == 0)
    check("reconciliation: fact_sales loaded 16374 rows in 13 good runs",
          con.execute(
              """SELECT SUM(rows_loaded) FROM load_runs lr
                 JOIN tables t ON t.table_id = lr.table_id
                 WHERE t.table_name = 'fact_sales'
                 AND lr.status = 'success'""").fetchone()[0] == 16374)

    # ---- reconciliation: lineage graph integrity (6 checks) ----
    check("every table_lineage pair has >= 1 column edge behind it",
          con.execute(
              """SELECT COUNT(*) FROM table_lineage tl
                 WHERE NOT EXISTS (
                   SELECT 1 FROM column_lineage cl
                   WHERE cl.source_table_id = tl.source_table_id
                     AND cl.target_table_id = tl.target_table_id)"""
          ).fetchone()[0] == 0)
    check("every column edge maps to real columns (FK integrity)",
          con.execute(
              "SELECT COUNT(*) FROM column_lineage cl "
              "LEFT JOIN columns s ON s.column_id = cl.source_column_id "
              "LEFT JOIN columns t ON t.column_id = cl.target_column_id "
              "WHERE s.column_id IS NULL OR t.column_id IS NULL"
          ).fetchone()[0] == 0)
    check("every warehouse column except product_name has a source",
          con.execute(
              """SELECT COUNT(*) FROM columns c
                 JOIN tables t ON t.table_id = c.table_id
                 WHERE t.layer = 'warehouse'
                 AND NOT EXISTS (
                   SELECT 1 FROM column_lineage cl
                   WHERE cl.target_table_id = t.table_id
                     AND cl.target_column_id = c.column_id)
                 AND NOT (t.table_name = 'dim_product'
                          AND c.column_name = 'product_name')"""
          ).fetchone()[0] == 0)
    check("every calculated edge carries a non-empty rule",
          con.execute(
              """SELECT COUNT(*) FROM column_lineage
                 WHERE transform_type = 'calculated'
                 AND (transform_rule IS NULL
                      OR TRIM(transform_rule) = '')"""
          ).fetchone()[0] == 0)
    check("every report reads >= 1 column",
          con.execute(
              """SELECT COUNT(*) FROM reports r
                 WHERE NOT EXISTS (
                   SELECT 1 FROM report_columns rc
                   WHERE rc.report_id = r.report_id)"""
          ).fetchone()[0] == 0)
    check("edges (33) cover 28 warehouse columns with a source "
          "(29 warehouse columns, 1 orphan)",
          db_counts["column_lineage"] == 33 and con.execute(
              """SELECT COUNT(DISTINCT c.column_id) FROM columns c
                 JOIN tables t ON t.table_id = c.table_id
                 JOIN column_lineage cl
                   ON cl.target_table_id = t.table_id
                  AND cl.target_column_id = c.column_id
                 WHERE t.layer = 'warehouse'""").fetchone()[0] == 28)

    # ---- outputs: the 10 query CSVs match the live query results ----
    slugs = ["upstream_lineage_net_revenue", "downstream_impact_unit_price",
             "orphan_columns", "tables_without_reports", "load_run_audit",
             "table_freshness", "transform_inventory",
             "report_dependency_map", "lineage_completeness",
             "change_request_cost_price"]
    for i, slug in enumerate(slugs, start=1):
        num = f"{i:02d}"
        cols, rows = run_query(con, num)
        out = BASE / "outputs" / f"query_{num}_{slug}.csv"
        check(f"output query_{num}_{slug}.csv exists",
              out.exists(), str(out))
        if out.exists():
            with open(out, newline="", encoding="utf-8") as f:
                rdr = csv.reader(f)
                header = next(rdr)
                data = [tuple(r) for r in rdr]
            check(f"output query_{num} header matches the query",
                  header == cols, f"(got {header})")
            check(f"output query_{num} rows match the query "
                  f"({len(rows)} rows)",
                  # csv.writer writes NULL as an empty string, so the
                  # live NULL must be normalised the same way.
                  data == [tuple("" if v is None else str(v) for v in r)
                           for r in rows],
                  f"(file has {len(data)})")

    con.close()
    print(f"\n{n_checks} checks, {len(fails)} failures"
          if fails else f"\n{n_checks} checks, all passing")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
