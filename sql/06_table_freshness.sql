-- 06 — Freshness: warehouse tables not loaded in the last 7 days.
-- Question: which tables are serving stale data — no good load inside
-- the last 7 days of the sample window?
-- Pattern: the window end is MAX(run_date) from the data itself, never
-- a hard-coded date, so the query stays correct on fresh data. A run
-- counts as a load only if it is not 'failed' (a failed run loads
-- nothing). A table with no load at all shows NULL and is stale too.
-- Expected result: 2 rows. dim_date last loaded 2026-11-02 (16 days
-- stale) and fact_returns last loaded 2026-11-08 (10 days stale).
-- dim_product is fresh by exactly one day (last good load 2026-11-11,
-- the window starts 2026-11-11) — worth watching, not yet stale.
WITH latest AS (
    SELECT t.table_name,
           MAX(CASE WHEN lr.status <> 'failed' THEN lr.run_date END)
               AS last_good_load
    FROM tables AS t
    LEFT JOIN load_runs AS lr ON lr.table_id = t.table_id
    WHERE t.layer = 'warehouse'
    GROUP BY t.table_name
),
window_end AS (
    SELECT MAX(run_date) AS end_date FROM load_runs
)
SELECT l.table_name,
       l.last_good_load,
       CAST(julianday(w.end_date) - julianday(l.last_good_load)
            AS INTEGER) AS days_since_load
FROM latest AS l, window_end AS w
WHERE l.last_good_load IS NULL
   OR l.last_good_load < date(w.end_date, '-7 days')
ORDER BY l.last_good_load;
