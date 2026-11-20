-- 07 — Transform inventory: pass-through vs calculated, with the rule text.
-- Question: which warehouse columns are copied as-is and which are
-- calculated — and what exactly is the calculation?
-- Pattern: a straight read of column_lineage, one row per edge, so the
-- rule text is visible next to the column it belongs to. A calculated
-- column with a vague rule ("cleaned", "fixed") is a smell; every
-- rule here states the formula or the rename.
-- Expected result: 33 rows — 19 pass-through edges and 14 calculated
-- edges. The calculated ones are the surrogate keys (customer_key,
-- product_key, sale_key), the date parts (date_key, month, year),
-- net_revenue (quantity x unit_price) and the four monthly aggregates.
SELECT tt.table_name AS target_table,
       tc.column_name AS target_column,
       st.table_name AS source_table,
       sc.column_name AS source_column,
       cl.transform_type,
       cl.transform_rule
FROM column_lineage AS cl
JOIN tables  AS tt ON tt.table_id = cl.target_table_id
JOIN columns AS tc ON tc.column_id = cl.target_column_id
JOIN tables  AS st ON st.table_id = cl.source_table_id
JOIN columns AS sc ON sc.column_id = cl.source_column_id
ORDER BY cl.transform_type, tt.table_name, tc.column_name;
