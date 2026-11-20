# Mini #20 — data dictionary (SAMPLE / DEMO only)

Fictional shop "Noor Electronics" — the same shop as Mini #1, Mini
#3, Mini #10 and Mini #15, so the numbers stay comparable. The
systems, the tables, the loads and every number are invented for
teaching — the lineage patterns are real, the business is not.
Build the database with `python3 src/build_db.py`; it reads the six
CSVs below and writes `data/processed/lineage.db` (the `.db` is
rebuilt, never uploaded — see `.gitignore`).

Sample window: 19 Oct – 18 Nov 2026 (30 load runs). All dates are ISO
`YYYY-MM-DD`; all money is PKR.

## data/raw/systems_SAMPLE.csv (4 rows)

| Column | Meaning |
|---|---|
| `system_id` | Short code: POS, WEB, SUP, XL (primary key) |
| `system_name` | Source system name |
| `system_type` | Always "Source system" here — these four feed the warehouse |
| `owner` | Person responsible for the system |
| `notes` | What the system holds |

## data/raw/tables_SAMPLE.csv (11 rows)

| Column | Meaning |
|---|---|
| `table_id` | Table number 1–11 (primary key) |
| `table_name` | Table name, e.g. `stg_pos_sales`, `fact_sales` |
| `layer` | `staging` (5 tables, raw as landed) or `warehouse` (6 tables, modelled) |
| `system_id` | Owning source system for staging tables; empty for warehouse tables |
| `description` | One line on what the table holds |

## data/raw/columns_SAMPLE.csv (51 rows)

| Column | Meaning |
|---|---|
| `column_id` | Column number 1–51 (primary key) |
| `table_name` | Table the column belongs to |
| `column_name` | Column name |
| `data_type` | SQLite type: INTEGER, TEXT or REAL |
| `is_key` | 1 if the column is a key (primary or surrogate), else 0 |
| `description` | What the column means; the planted gap is marked here |

## data/raw/lineage_SAMPLE.csv (33 rows)

One row per column-level lineage edge — source column → target
column.

| Column | Meaning |
|---|---|
| `edge_id` | Edge number 1–33 (primary key) |
| `source_table` / `source_column` | Where the value comes from |
| `target_table` / `target_column` | Where the value lands |
| `transform_type` | `pass-through` (copied as-is, sometimes renamed) or `calculated` (a formula was applied) |
| `transform_rule` | The rule in words — the formula for calculated edges, "Copied as-is" or the rename for pass-through edges |

19 edges are pass-through, 14 are calculated. A target column can
have two source edges: `fact_sales.quantity` and
`fact_sales.unit_price` each come from both POS and website
(the two feeds are unioned), and `fact_sales.net_revenue` has four
source edges (quantity and unit_price from both feeds).

## data/raw/load_runs_SAMPLE.csv (30 rows)

One row per load run — the audit trail.

| Column | Meaning |
|---|---|
| `run_id` | Run id `LR-01` … `LR-30` (primary key) |
| `table_name` | Warehouse table that was loaded |
| `run_date` | Load date (ISO) |
| `started_at` / `finished_at` | Run times (HH:MM) |
| `rows_loaded` | Rows written to the table |
| `rows_rejected` | Rows that failed validation and were dropped |
| `status` | `success`, `failed` or `partial` |
| `notes` | Why a run failed or was partial (empty on clean runs) |

27 runs succeeded, 2 failed, 1 was partial. 18,598 rows were loaded
in total and 57 rejected. `fact_sales` loaded 16,374 rows across its
13 successful runs.

## data/raw/reports_SAMPLE.csv (6 rows)

One row per report. `uses_tables` and `uses_columns` are
semicolon-separated lists; `build_db.py` splits them into the
`report_columns` junction table (20 links) and the table list is
derived from the columns, so the two lists can never disagree.

| Column | Meaning |
|---|---|
| `report_id` | Report id `R1` … `R6` (primary key) |
| `report_name` | Report name |
| `owner` | Person responsible for the report |
| `refresh_cadence` | Daily, Weekly or Monthly |
| `uses_tables` | Warehouse tables the report reads |
| `uses_columns` | Exact `table.column` pairs the report reads |

## The lineage database (`data/processed/lineage.db`)

Built by `src/build_db.py` from the CSVs above plus `sql/schema.sql`.
Eight tables:

| Table | Rows | What it holds |
|---|---|---|
| `systems` | 4 | Source systems |
| `tables` | 11 | Staging + warehouse tables |
| `columns` | 51 | Every column in every table |
| `column_lineage` | 33 | Column-level edges (from `lineage_SAMPLE.csv`) |
| `table_lineage` | 11 | Table-level edges — DERIVED in `build_db.py` as the distinct source → target table pairs from `column_lineage`, so every table edge is backed by at least one column edge |
| `load_runs` | 30 | The audit trail |
| `reports` | 6 | Reports |
| `report_columns` | 20 | Which report reads which column (from `reports_SAMPLE.csv`) |

## The 3 planted gaps (recorded here, found by the queries)

1. **A column with no source** — `dim_product.product_name` has no
   incoming lineage edge (query 03 finds exactly 1 orphan column).
   It is the only warehouse column without a source.
2. **A table with no downstream report** — `fact_returns` is loaded
   but read by no report (query 04 finds exactly 1 dead table).
3. **A lying audit row** — run `LR-08` (`fact_sales`, 2026-11-12)
   is marked `success` with 37 rows rejected (query 05 finds exactly
   1 lying row).

Two more honest findings ride along: 2 failed runs (LR-06, LR-22),
1 partial run (LR-28), and 2 stale tables (dim_date 16 days,
fact_returns 10 days — query 06).

## Totals (verified by `src/checks.py`, 98 checks)

- 4 systems · 11 tables (5 staging, 6 warehouse) · 51 columns
- 33 column edges (19 pass-through, 14 calculated) · 11 table edges
- 30 load runs (27 success, 2 failed, 1 partial) · 6 reports · 20 report-column links
- 18,598 rows loaded · 57 rows rejected
- Lineage completeness: 96.55% overall (28 of 29 warehouse columns);
  `dim_product` 80.00%, all other warehouse tables 100.00%
