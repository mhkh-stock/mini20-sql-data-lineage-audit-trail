# Mini #20 — lineage findings (plain English)

**SAMPLE / DEMO data only.** Fictional shop (Noor Electronics),
fictional systems, fictional numbers. Every figure below was
recomputed by `src/checks.py` (98 checks, all passing) from the
database built by `src/build_db.py` — nothing here is hand-typed.

## The warehouse in one paragraph

Four source systems (POS tills, website orders, supplier price sheet,
manual Excel adjustments) feed 5 staging tables, which feed 6
warehouse tables (3 dimensions, fact_sales, fact_returns and a monthly
aggregate). The lineage model records 51 columns, 33 column-level
edges and 11 table-level edges, and 6 reports read 20 columns across
those tables. In the sample window (19 Oct – 18 Nov 2026),
30 loads ran: 27 succeeded, 2 failed, 1 was partial. In total
18,598 rows were loaded and 57 were rejected.

## The 3 planted gaps — what the audit actually found

### 1. One column has no source: `dim_product.product_name`

Every warehouse column traces back to a source except one. The
product display name is typed in by hand somewhere and no system
feeds it — so if a product name is wrong in a report, there is no
upstream system to check it against. Lineage completeness for
`dim_product` is 80.00% (4 of 5 columns); every other warehouse
table is 100.00%, and overall completeness is 96.55% (28 of 29
columns). Fix: point `product_name` at the supplier sheet (or at
the website catalogue) and add the edge — one row in
`lineage_SAMPLE.csv`.

### 2. One table is loaded but never read: `fact_returns`

Returns are loaded (3 runs, 125 rows) but no report uses the table —
it has no downstream report at all (query 04). The business cannot
see refunds anywhere, even though the data exists. Fix first by
deciding: either build the Returns & Refunds report on it, or stop
loading it and say so. A table nobody reads is either a missing
report or wasted load.

### 3. One audit row is lying: run LR-08, `fact_sales`, 2026-11-12

The run is marked `success` but rejected 37 rows. A success with
rejected rows is a contradiction — rejected rows are lost data, so
the run cannot honestly be called a success. It is the only lying
row in the 30 runs. Fix: make the loader set `status = 'partial'`
whenever `rows_rejected > 0` (query 05 finds these rows with one
WHERE clause — add the same condition to the loader's own check).

## The other two load problems

- **LR-06, `fact_sales`, 2026-11-10 — failed.** The POS export did
  not arrive, so 0 rows loaded that day. One day of sales is missing
  from the warehouse until the export is re-sent.
- **LR-22, `dim_product`, 2026-11-15 — failed.** The supplier sheet
  had 18 rows with a negative `cost_price`; 0 rows loaded. The sheet
  needs a validation rule (cost_price > 0) before it is accepted.
- **LR-28, `agg_monthly_sales`, 2026-11-17 — partial.** 2 product
  keys were missing from `dim_product`, so the monthly totals exclude
  them. The aggregate is understated until those products are added
  to the dimension.

## Freshness: two tables are stale

Measured against the last run date in the sample (2026-11-18):

| Table | Last good load | Days stale |
|---|---|---|
| `dim_date` | 2026-11-02 | 16 |
| `fact_returns` | 2026-11-08 | 10 |

`dim_date` has not been rebuilt in over two weeks — new sale dates
are not in the calendar dimension. `fact_returns` is stale too, which
fits finding 2: nobody notices, because nobody reads it. Watch
`dim_product` as well: its last good load was 2026-11-11, exactly on
the 7-day line — fresh today, stale tomorrow if it does not run.

## What breaks if a column changes

- **`stg_pos_sales.unit_price` changes** (query 02): 4 warehouse
  columns are affected — `fact_sales.unit_price`,
  `fact_sales.net_revenue`, `agg_monthly_sales.avg_unit_price` and
  `agg_monthly_sales.total_revenue` — and 5 of the 6 reports must be
  re-tested (Daily Sales Dashboard, Customer Retention Report,
  Monthly Revenue Report, Product Margin Report, Executive KPI
  Summary). Only Supplier Cost Watch is untouched.
- **`stg_supplier_prices.cost_price` changes** (query 10): only
  `dim_product.supplier_cost` depends on it, so only 2 reports must
  be re-tested — Product Margin Report and Supplier Cost Watch.
- **`fact_sales.net_revenue` comes from** (query 01): 4 source
  columns — `quantity` and `unit_price` from both the POS tills and
  the website orders — all through the calculated rule
  `quantity x unit_price summed over POS and website`.

## Transforms: mostly copy, some maths

Of the 33 lineage edges, 19 are pass-through (copied as-is, sometimes
renamed) and 14 are calculated. The calculated ones are the three
surrogate keys (`customer_key`, `product_key`, `sale_key`), the date
parts (`date_key`, `month`, `year`), `net_revenue`
(`quantity x unit_price`) and the four monthly aggregates
(`SUM(quantity)`, `SUM(net_revenue)`, `AVG(unit_price)` and the
`YYYYMM` month key). Every calculated edge carries its rule in
writing (query 07) — there is no "cleaned" or "fixed" without a
formula.

## What to fix first (in order)

1. **Fix the lying audit row** — make the loader mark a run
   `partial` when `rows_rejected > 0`. A lying success hides lost
   data; it is the cheapest fix and the most dangerous gap.
2. **Give `product_name` a source** — one lineage edge, and
   completeness goes to 100%.
3. **Rebuild `dim_date`** — 16 days stale; every date-based report
   is reading an old calendar.
4. **Decide on `fact_returns`** — build the returns report or stop
   loading the table. Either way, stop paying for a load nobody
   reads.
5. **Validate the supplier sheet** (`cost_price > 0`) before load,
   so LR-22 cannot happen again.
