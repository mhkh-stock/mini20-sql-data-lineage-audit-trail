-- 05 — Load-run audit: failed / partial runs and the lying success row.
-- Question: which loads did NOT go cleanly — and does any run claim
-- success while the numbers say otherwise?
-- Pattern: one WHERE clause for the three bad shapes — status failed,
-- status partial, or status success with rows_rejected > 0. A success
-- with rejected rows is a contradiction: rejected rows mean data was
-- lost, so the run cannot honestly be called a success.
-- Expected result: 4 rows. 2 failed (fact_sales 2026-11-10, POS export
-- missing; dim_product 2026-11-15, 18 bad supplier rows), 1 partial
-- (agg_monthly_sales 2026-11-17, 2 product keys missing) and 1 lying
-- success (fact_sales 2026-11-12, 37 rows rejected, still marked
-- success). The lying row is planted gap #3 (see data/README.md).
SELECT lr.run_id,
       t.table_name,
       lr.run_date,
       lr.rows_loaded,
       lr.rows_rejected,
       lr.status,
       CASE
           WHEN lr.status = 'success' AND lr.rows_rejected > 0
               THEN 'LYING SUCCESS ROW'
           WHEN lr.status = 'failed' THEN 'FAILED RUN'
           ELSE 'PARTIAL RUN'
       END AS finding,
       lr.notes
FROM load_runs AS lr
JOIN tables AS t ON t.table_id = lr.table_id
WHERE lr.status IN ('failed', 'partial')
   OR (lr.status = 'success' AND lr.rows_rejected > 0)
ORDER BY lr.run_date, t.table_name;
