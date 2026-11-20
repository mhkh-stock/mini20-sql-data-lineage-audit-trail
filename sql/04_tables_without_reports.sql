-- 04 — Tables with no downstream report (dead tables).
-- Question: which warehouse tables does no report use — data that is
-- loaded every week but never read by anyone?
-- Pattern: NOT EXISTS against report_columns (joined through columns
-- to reach the table). Scoped to the warehouse layer: staging tables
-- are feeds, not report sources, so they are never expected to have
-- a report.
-- Expected result: exactly 1 row — fact_returns. Returns are loaded
-- (3 runs) but no report reads them, so the returns story is invisible
-- to the business. This is planted gap #2 (see data/README.md).
SELECT t.table_name,
       t.layer,
       t.description
FROM tables AS t
WHERE t.layer = 'warehouse'
  AND NOT EXISTS (
      SELECT 1
      FROM report_columns AS rc
      JOIN columns AS c ON c.column_id = rc.column_id
      WHERE c.table_id = t.table_id
  )
ORDER BY t.table_name;
