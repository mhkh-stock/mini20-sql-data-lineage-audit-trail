-- 02 — Downstream impact: everything that breaks if stg_pos_sales.unit_price changes.
-- Question: a source column is about to change — which warehouse
-- columns and which reports depend on it, directly or through
-- another column?
-- Pattern: a RECURSIVE CTE walks column_lineage forwards from the
-- source column; the result is joined to report_columns so every
-- impacted column also names the reports that read it. A report
-- listed here must be re-tested after the change. The report list is
-- built with a correlated GROUP_CONCAT over an ORDER BY subquery so
-- the order is deterministic across runs.
-- Expected result: 4 impacted columns. Depth 1: fact_sales.unit_price
-- (pass-through) and fact_sales.net_revenue (calculated). Depth 2:
-- agg_monthly_sales.avg_unit_price (from unit_price) and
-- agg_monthly_sales.total_revenue (from net_revenue). Reports touched:
-- Daily Sales Dashboard, Customer Retention Report, Monthly Revenue
-- Report, Product Margin Report and Executive KPI Summary — 5 of the
-- 6 reports. Only Supplier Cost Watch is untouched (it reads
-- dim_product, not fact_sales).
WITH RECURSIVE downstream (
    source_table, source_column,
    target_table, target_column,
    transform_type, depth
) AS (
    SELECT st.table_name, sc.column_name,
           tt.table_name, tc.column_name,
           cl.transform_type, 1
    FROM column_lineage AS cl
    JOIN tables  AS st ON st.table_id = cl.source_table_id
    JOIN columns AS sc ON sc.column_id = cl.source_column_id
    JOIN tables  AS tt ON tt.table_id = cl.target_table_id
    JOIN columns AS tc ON tc.column_id = cl.target_column_id
    WHERE st.table_name = 'stg_pos_sales'
      AND sc.column_name = 'unit_price'
    UNION ALL
    SELECT st.table_name, sc.column_name,
           tt.table_name, tc.column_name,
           cl.transform_type, d.depth + 1
    FROM column_lineage AS cl
    JOIN tables  AS st ON st.table_id = cl.source_table_id
    JOIN columns AS sc ON sc.column_id = cl.source_column_id
    JOIN tables  AS tt ON tt.table_id = cl.target_table_id
    JOIN columns AS tc ON tc.column_id = cl.target_column_id
    JOIN downstream AS d
      ON d.target_table = st.table_name
     AND d.target_column = sc.column_name
)
SELECT d.target_table,
       d.target_column,
       d.transform_type,
       d.depth,
       (SELECT GROUP_CONCAT(rn, '; ')
        FROM (SELECT DISTINCT r2.report_name AS rn
              FROM report_columns AS rc2
              JOIN columns AS c2 ON c2.column_id = rc2.column_id
              JOIN tables  AS t2 ON t2.table_id = c2.table_id
              JOIN reports AS r2 ON r2.report_id = rc2.report_id
              WHERE t2.table_name = d.target_table
                AND c2.column_name = d.target_column
              ORDER BY rn)) AS reports_using_it
FROM downstream AS d
GROUP BY d.target_table, d.target_column, d.transform_type, d.depth
ORDER BY d.depth, d.target_table, d.target_column;
