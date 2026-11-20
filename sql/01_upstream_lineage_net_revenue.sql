-- 01 — Upstream lineage of one KPI column: fact_sales.net_revenue.
-- Question: where does net_revenue actually come from — which source
-- systems, which source columns, and through which transforms?
-- Pattern: a RECURSIVE CTE walks column_lineage backwards from the
-- target column until it reaches staging columns (which have no
-- incoming edge). The same query works for any column: change the
-- two values in the anchor WHERE clause.
-- Expected result: 4 rows. net_revenue is quantity x unit_price summed
-- over POS and website, so its sources are stg_pos_sales.quantity,
-- stg_pos_sales.unit_price, stg_web_orders.quantity and
-- stg_web_orders.unit_price — systems POS and WEB, all four edges
-- transform_type = 'calculated', all at depth 1.
WITH RECURSIVE upstream (
    target_table, target_column,
    source_table, source_column,
    transform_type, transform_rule, depth
) AS (
    SELECT tt.table_name, tc.column_name,
           st.table_name, sc.column_name,
           cl.transform_type, cl.transform_rule, 1
    FROM column_lineage AS cl
    JOIN tables  AS tt ON tt.table_id = cl.target_table_id
    JOIN columns AS tc ON tc.column_id = cl.target_column_id
    JOIN tables  AS st ON st.table_id = cl.source_table_id
    JOIN columns AS sc ON sc.column_id = cl.source_column_id
    WHERE tt.table_name = 'fact_sales'
      AND tc.column_name = 'net_revenue'
    UNION ALL
    SELECT tt.table_name, tc.column_name,
           st.table_name, sc.column_name,
           cl.transform_type, cl.transform_rule, u.depth + 1
    FROM column_lineage AS cl
    JOIN tables  AS tt ON tt.table_id = cl.target_table_id
    JOIN columns AS tc ON tc.column_id = cl.target_column_id
    JOIN tables  AS st ON st.table_id = cl.source_table_id
    JOIN columns AS sc ON sc.column_id = cl.source_column_id
    JOIN upstream AS u
      ON u.source_table = tt.table_name
     AND u.source_column = tc.column_name
)
SELECT u.source_table,
       u.source_column,
       t.system_id AS source_system,
       u.transform_type,
       u.transform_rule,
       u.depth
FROM upstream AS u
JOIN tables AS t ON t.table_name = u.source_table
ORDER BY u.depth, u.source_table, u.source_column;
