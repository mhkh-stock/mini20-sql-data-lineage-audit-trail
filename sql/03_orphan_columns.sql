-- 03 — Orphan columns: warehouse columns with no lineage edge.
-- Question: which columns in the warehouse have no recorded source —
-- so nobody can say where their values come from?
-- Pattern: NOT EXISTS against column_lineage. Scoped to the warehouse
-- layer on purpose: staging columns are the roots of the graph (their
-- source is the source system itself, not another table), so they are
-- not orphans — only a warehouse column with no incoming edge is one.
-- Expected result: exactly 1 row — dim_product.product_name. The
-- product display name is typed in by hand somewhere and no system
-- feeds it; every other warehouse column has a source. This is
-- planted gap #1 (see data/README.md).
SELECT t.table_name,
       c.column_name,
       c.data_type,
       c.description
FROM columns AS c
JOIN tables AS t ON t.table_id = c.table_id
WHERE t.layer = 'warehouse'
  AND NOT EXISTS (
      SELECT 1 FROM column_lineage AS cl
      WHERE cl.target_table_id = t.table_id
        AND cl.target_column_id = c.column_id
  )
ORDER BY t.table_name, c.column_name;
