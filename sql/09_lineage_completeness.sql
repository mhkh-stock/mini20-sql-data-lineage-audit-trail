-- 09 — Lineage completeness score per warehouse table.
-- Question: for each warehouse table, what share of its columns has a
-- recorded source — and where is the documentation thinnest?
-- Pattern: LEFT JOIN from columns to column_lineage, counting DISTINCT
-- columns that have at least one incoming edge (a column fed by two
-- sources, like fact_sales.quantity, still counts once). The score is
-- a plain percentage, so it can be tracked over time like any KPI.
-- Expected result: 6 rows. dim_product scores 80.00% (4 of 5 columns —
-- product_name has no source); every other warehouse table scores
-- 100.00%. Overall warehouse completeness is 28 of 29 columns,
-- 96.55%.
SELECT t.table_name,
       COUNT(DISTINCT c.column_id) AS columns_total,
       COUNT(DISTINCT CASE WHEN cl.edge_id IS NOT NULL
                           THEN c.column_id END) AS columns_with_source,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN cl.edge_id IS NOT NULL
                                         THEN c.column_id END)
             / COUNT(DISTINCT c.column_id), 2) AS completeness_pct
FROM tables AS t
JOIN columns AS c ON c.table_id = t.table_id
LEFT JOIN column_lineage AS cl
       ON cl.target_table_id = t.table_id
      AND cl.target_column_id = c.column_id
WHERE t.layer = 'warehouse'
GROUP BY t.table_name
ORDER BY completeness_pct ASC, t.table_name;
