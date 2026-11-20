# Mini #20 — SQL Data Lineage & Audit Trail Pack

**Status:** live on GitHub
(https://github.com/mhkh-stock/mini20-sql-data-lineage-audit-trail) — published Fri 20 Nov 2026.

**SAMPLE / DEMO data only.** Fictional shop, fictional systems,
fictional numbers. Never claimed as real client work.

The lineage companion to Mini #15's advanced-patterns pack: the same
"Noor Electronics" shop, now modelled as a small warehouse — 4 source
systems (POS tills, website orders, supplier price sheet, manual
Excel) → 5 staging tables → 6 warehouse tables → 6 reports. Ten SQL
queries, one business question per file, each answering a question a
data team actually asks: where does this KPI come from, what breaks
if this column changes, which columns have no source, which tables
does nobody read, and can the load audit be trusted.

## Why this pack

Data Lineage holds at 11.8% of London contract data-analyst ads
(daily market watch, 20 Nov 2026), the migration cluster is intact
(Migration 19.7%, Data Migration 15.2%), and ETL holds in the
contract top 30 a fifth day — lineage and audit are named, unbuilt
skills in this library, so this pack builds them.

## Business question

"If this column changes, what breaks?"

## What is inside

| File | What it does |
|---|---|
| `outputs/lineage_findings.md` | The findings write-up: the 3 gaps, the dead table, the lying audit row, the completeness scores, what to fix first |
| `outputs/query_01_…_query_10_….csv` | The 10 query results, one CSV per query |
| `data/raw/*_SAMPLE.csv` | The 6 SAMPLE files the database is built from |
| `data/README.md` | Data dictionary + the 3 planted gaps, recorded |
| `data/processed/lineage.db` | The built SQLite database (rebuildable, not uploaded) |
| `sql/schema.sql` | The 8-table lineage schema |
| `sql/01_…_10_….sql` | The 10 queries, one business question per file |
| `src/build_db.py` | Builds `lineage.db` from the CSVs + schema, prints row counts |
| `src/run_queries.py` | Runs all 10 queries, writes the 10 output CSVs |
| `src/checks.py` | Checks as code — 98 checks, all passing |
| `requirements.txt` | Standard library only — nothing to install |
| `.gitignore` | Excludes `*.db` — the database rebuilds from the scripts |

## Key findings (verified numbers)

- **One column has no source:** `dim_product.product_name` is the
  only orphan warehouse column — lineage completeness is 96.55%
  overall (28 of 29 columns); `dim_product` scores 80.00%, every
  other warehouse table 100.00%.
- **One table is loaded but never read:** `fact_returns` (3 runs,
  125 rows) has no downstream report — the returns story is
  invisible to the business.
- **One audit row is lying:** run LR-08 (`fact_sales`, 2026-11-12)
  is marked `success` with 37 rows rejected. Of the 30 runs, 27
  succeeded, 2 failed and 1 was partial; 18,598 rows loaded,
  57 rejected in total.
- **Two tables are stale:** `dim_date` (16 days, last load
  2026-11-02) and `fact_returns` (10 days, last load 2026-11-08).
- **One price change touches 5 of 6 reports:** changing
  `stg_pos_sales.unit_price` affects 4 warehouse columns and 5
  reports; changing the supplier `cost_price` touches only 2
  reports (Product Margin Report, Supplier Cost Watch).

## The 10 queries

| # | File | Business question | Verified output |
|---|---|---|---|
| 1 | `01_upstream_lineage_net_revenue.sql` | Where does `fact_sales.net_revenue` come from? | 4 source columns, systems POS + WEB, all calculated |
| 2 | `02_downstream_impact_unit_price.sql` | What breaks if `stg_pos_sales.unit_price` changes? | 4 impacted columns, 5 reports to re-test |
| 3 | `03_orphan_columns.sql` | Which warehouse columns have no source? | 1 row: `dim_product.product_name` |
| 4 | `04_tables_without_reports.sql` | Which tables does no report use? | 1 row: `fact_returns` |
| 5 | `05_load_run_audit.sql` | Which loads failed, and is any success a lie? | 4 rows: 2 failed, 1 partial, 1 lying success |
| 6 | `06_table_freshness.sql` | Which tables have not loaded in 7 days? | 2 rows: `dim_date` 16 days, `fact_returns` 10 days |
| 7 | `07_transform_inventory.sql` | Which columns are copied vs calculated, and how? | 33 rows: 19 pass-through, 14 calculated |
| 8 | `08_report_dependency_map.sql` | What does each report read? | 6 reports, 13 report-table pairs |
| 9 | `09_lineage_completeness.sql` | How complete is the lineage, per table? | 6 rows: `dim_product` 80.00%, rest 100.00% |
| 10 | `10_change_request_cost_price.sql` | The supplier changes `cost_price` — what must be re-tested? | 2 reports: Product Margin Report, Supplier Cost Watch |

## What the pack teaches

1. **Lineage is a graph, not a document.** Upstream (query 01) and
   downstream (query 02) are the same recursive-CTE walk in opposite
   directions — once the edges are in a table, both questions are
   one query each.
2. **An audit trail that cannot lie is worth more than a dashboard.**
   Query 05 finds the lying success row with one WHERE clause; the
   fix is one rule in the loader (rejected rows ⇒ not success).
3. **Completeness is a KPI.** Query 09 scores every table like any
   other metric — 96.55% today, 100% when `product_name` gets its
   one missing edge.
4. **Staleness is a fact, not a feeling.** Query 06 derives its
   7-day window from the data's own last run date, so it stays
   correct on fresh data — and it shows `dim_product` is fresh by
   exactly one day.
5. **A change request is a query, not a meeting.** Query 10 takes
   one source column and returns the exact re-test list — change
   the two values in its `params` CTE to test any other column.

## Verified numbers

| KPI | Value |
|---|---|
| Source systems | 4 (POS, WEB, SUP, XL) |
| Tables | 11 (5 staging, 6 warehouse) |
| Columns | 51 |
| Lineage edges | 33 column-level + 11 table-level |
| Load runs | 30 (27 success, 2 failed, 1 partial) |
| Rows loaded / rejected | 18,598 / 57 |
| Reports | 6, reading 20 columns |
| Orphan columns | 1 (`dim_product.product_name`) |
| Tables without a report | 1 (`fact_returns`) |
| Lying audit rows | 1 (LR-08, 37 rejected, marked success) |
| Stale tables | 2 (`dim_date` 16 days, `fact_returns` 10 days) |
| Lineage completeness | 96.55% overall; `dim_product` 80.00%, rest 100.00% |
| Transform split | 19 pass-through / 14 calculated |
| Checks | 98 passing (`python3 src/checks.py`) |

Verification: `python3 src/checks.py` — every headline number is
recomputed from the CSVs and the database and compared against every
query output: base counts agree between CSV and DB; the 3 planted
gaps are found exactly (1 orphan, 1 dead table, 1 lying row); query
outputs match hand-verified expectations (Q01's 4 sources, Q02's 4
impacted columns and 5 reports, Q05's 2+1+1, Q06's 16 and 10 days,
Q07's 19/14 split, Q08's per-report table sets, Q09's 80.00% and
96.55%, Q10's 2 reports); totals reconcile (18,598 loaded, 57
rejected, 27/2/1 statuses); every table edge is backed by a column
edge; every output CSV is byte-compared against a fresh run of its
query (see `src/checks.py`).

## How to run it

1. `cd mini20-sql-data-lineage-audit-trail`
2. `python3 src/build_db.py` — builds `data/processed/lineage.db`
   from the SAMPLE CSVs.
3. `python3 src/run_queries.py` — runs all 10 queries, writes
   `outputs/query_*.csv`.
4. `python3 src/checks.py` — 98 checks, all passing.
5. Run any query by hand, e.g.
   `sqlite3 -header -column data/processed/lineage.db < sql/05_load_run_audit.sql`

Requires Python 3 + SQLite (standard library only, nothing to
install). Verified on SQLite 3.45.1.

## Two traps this pack teaches

- **A success with rejected rows is a lie, not a success.** The
  audit table will happily store any status string — the check
  belongs in the loader (`rows_rejected > 0` ⇒ `partial`), and
  query 05 is the test that proves the loader does it.
- **A count over a join counts rows, not things.** Query 09's
  completeness score must use `COUNT(DISTINCT column_id)` for the
  denominator — a plain `COUNT` counts one row per lineage edge,
  so a column with 4 sources (like `net_revenue`) counts 4 times
  and the score comes out wrong (58.33% instead of 100%).

## Limits

- **SAMPLE data only.** The shop, the systems and the loads are
  fictional; the "findings" are the story the planted gaps were
  designed to tell. The SQL patterns are real.
- **SQLite only** — the recursive CTEs, `FILTER`-free aggregates
  and `julianday` freshness maths are SQLite-flavoured; the same
  model ports to PostgreSQL with the same tables.
- **One sample window (19 Oct – 18 Nov 2026)** — freshness is
  measured against the data's own last run date, so the query stays
  honest on new data, but the window itself is fixed.
- **No real load job** — `load_runs` is a seeded audit table, not
  a live pipeline log. The pack audits the trail; it does not run
  the loads.

## Published

Published Fri 20 Nov 2026: https://github.com/mhkh-stock/mini20-sql-data-lineage-audit-trail

The built `data/processed/lineage.db` is intentionally not uploaded —
rebuild it any time with `python3 src/build_db.py`.
