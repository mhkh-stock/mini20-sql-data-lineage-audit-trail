-- 10 — The "change request" query: given a source column, list every report that must be re-tested.
-- Question: the supplier changes cost_price — which reports have to be
-- re-tested before the new prices go live?
-- Pattern: the same forward recursive walk as query 02, but starting
-- from a source column named once in the params CTE — change the two
-- values there to test any other source column — then join the
-- impacted columns to the reports that read them.
-- Expected result: 2 rows. cost_price feeds dim_product.supplier_cost
-- and nothing else downstream, so only the two reports that read
-- supplier_cost must be re-tested: Product Margin Report and Supplier
-- Cost Watch.
WITH params AS (
    SELECT 'stg_supplier_prices' AS src_table,
           'cost_price' AS src_column
),
downstream (
    source_table, source_column,
    target_table, target_column, depth
) AS (
    SELECT st.table_name, sc.column_name,
           tt.table_name, tc.column_name, 1
    FROM column_lineage AS cl
    JOIN tables  AS st ON st.table_id = cl.source_table_id
    JOIN columns AS sc ON sc.column_id = cl.source_column_id
    JOIN tables  AS tt ON tt.table_id = cl.target_table_id
    JOIN columns AS tc ON tc.column_id = cl.target_column_id
    WHERE st.table_name = (SELECT src_table FROM params)
      AND sc.column_name = (SELECT src_column FROM params)
    UNION ALL
    SELECT st.table_name, sc.column_name,
           tt.table_name, tc.column_name, d.depth + 1
    FROM column_lineage AS cl
    JOIN tables  AS st ON st.table_id = cl.source_table_id
    JOIN columns AS sc ON sc.column_id = cl.source_column_id
    JOIN tables  AS tt ON tt.table_id = cl.target_table_id
    JOIN columns AS tc ON tc.column_id = cl.target_column_id
    JOIN downstream AS d
      ON d.target_table = st.table_name
     AND d.target_column = sc.column_name
)
SELECT DISTINCT r.report_name,
       r.owner,
       r.refresh_cadence
FROM downstream AS d
JOIN tables  AS t  ON t.table_name = d.target_table
JOIN columns AS c  ON c.table_id = t.table_id
                   AND c.column_name = d.target_column
JOIN report_columns AS rc ON rc.column_id = c.column_id
JOIN reports AS r ON r.report_id = rc.report_id
ORDER BY r.report_name;
