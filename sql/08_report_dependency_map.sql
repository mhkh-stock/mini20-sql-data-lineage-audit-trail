-- 08 — Report dependency map: each report's full table list.
-- Question: for every report, which warehouse tables does it actually
-- read — so a table change can be traced to the reports it touches?
-- Pattern: report_columns is joined through columns to tables; the
-- per-report table list is built with a correlated GROUP_CONCAT over
-- a DISTINCT subquery, because one report can read two columns from
-- the same table and the table must still appear once.
-- Expected result: 6 rows, one per report. Daily Sales Dashboard reads
-- fact_sales, dim_date, dim_product; Monthly Revenue Report reads
-- agg_monthly_sales, dim_product; Customer Retention Report reads
-- dim_customer, fact_sales; Product Margin Report reads dim_product,
-- fact_sales; Executive KPI Summary reads agg_monthly_sales,
-- fact_sales, dim_customer; Supplier Cost Watch reads dim_product
-- only. 13 report-table pairs in total.
SELECT r.report_id,
       r.report_name,
       r.owner,
       r.refresh_cadence,
       (SELECT GROUP_CONCAT(tn, ', ')
        FROM (SELECT DISTINCT t2.table_name AS tn
              FROM report_columns AS rc2
              JOIN columns AS c2 ON c2.column_id = rc2.column_id
              JOIN tables  AS t2 ON t2.table_id = c2.table_id
              WHERE rc2.report_id = r.report_id
              ORDER BY tn)) AS tables_used,
       COUNT(rc.column_id) AS columns_used
FROM reports AS r
LEFT JOIN report_columns AS rc ON rc.report_id = r.report_id
GROUP BY r.report_id, r.report_name, r.owner, r.refresh_cadence
ORDER BY r.report_name;
