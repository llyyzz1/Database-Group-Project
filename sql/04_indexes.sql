-- ============================================================
-- 04_indexes.sql  --  Index experiment: switching between three structures
-- ============================================================
-- This file contains 5 independent sections. RUN ONLY ONE SECTION AT A TIME.
-- When driven programmatically (05_benchmark.py / 06_query_form_comparison.py),
-- the sections are picked up automatically via the `-- ### SECTION:` markers,
-- so no manual work is needed.
--
-- The three structures:
--   A  Reference baseline = 01_schema.sql as submitted (14 indexes, 6 of them
--                           created automatically by the foreign keys)
--   B  No-index baseline  = A with every foreign-key index removed
--                           (drop the FK constraint first, then the index;
--                            a bare DROP INDEX fails with ERROR 1553)
--   C  Optimized          = A plus 4 composite / covering indexes with a
--                           business justification
--
-- IMPORTANT: the indexes in structure A are NOT created by us. They are produced
--            automatically by PRIMARY KEY / UNIQUE / FOREIGN KEY in 01_schema.sql.
--            So the "adding indexes" experiment only concerns structure C.
-- ============================================================
--
-- READ THIS BEFORE RUNNING ANY SECTION MANUALLY
-- The three error codes you may hit, and what each one means:
--
--   ERROR 1061  Duplicate key name 'ix_xxx'
--       -> You are RE-RUNNING apply_optimized; the index already exists.
--          This is not a failure. You are already in structure C.
--          Go straight to measuring, or run revert_optimized to go back to A.
--
--   ERROR 1091  Can't DROP 'ix_xxx'; check that column/key exists
--       -> You are running revert_optimized but you are NOT in structure C
--          (the index does not exist at all). You are already in structure A.
--
--   ERROR 1553  Cannot drop index ... needed in a foreign key constraint
--       -> You skipped the DROP FOREIGN KEY statements in revert_optimized.
--          The required order is: drop the FK constraint -> drop the index ->
--          add the FK constraint back.
--
--   Run one section per execution. Use show_state below to check where you are.
-- ============================================================


-- ### SECTION: show_state -> read-only, changes nothing
-- Run this to find out which structure you are currently in. Recommended before
-- any manual operation. How to read the result:
--   14 indexes, no index starting with ix_      -> structure A (baseline)
--   15 indexes, 4 indexes starting with ix_      -> structure C (indexes added)
--    9 indexes, only PRIMARY left on orders/product -> structure B

SELECT COUNT(DISTINCT table_name, index_name) AS index_count,
       CONCAT('Structure ',
              CASE WHEN COUNT(DISTINCT CASE WHEN index_name LIKE 'ix\_%'
                                            THEN index_name END) >= 4
                        THEN 'C (4 business indexes added)'
                   WHEN COUNT(DISTINCT table_name, index_name) <= 9
                        THEN 'B (foreign-key indexes removed)'
                   ELSE 'A (reference baseline)' END) AS current_structure
FROM information_schema.STATISTICS
WHERE table_schema = DATABASE();

SELECT table_name, index_name,
       GROUP_CONCAT(column_name ORDER BY seq_in_index) AS cols
FROM information_schema.STATISTICS
WHERE table_schema = DATABASE()
GROUP BY table_name, index_name
ORDER BY table_name, index_name;


-- ### SECTION: apply_optimized -> A becomes C
-- Adds the 4 indexes that the reference DDL does not have. Each one targets a
-- specific query in the workload; the reasoning is in the comment above it.
-- Run ANALYZE TABLE afterwards, otherwise the optimizer statistics are not updated.
-- (Re-running this section raises ERROR 1061, meaning you already did it. It does
--  not affect the data.)
--
-- MEASURED FINDING (important, worth writing up in the report):
--   When a new index can replace an automatically created foreign-key index,
--   MySQL DELETES the old foreign-key index by itself.
--   After running this section on structure A the index count goes from 14 to 15,
--   not to 14 + 4 = 18:
--       order_item.fk_item_product  replaced by ix_oi_pid_oid    -> dropped
--       orders.fk_order_customer    replaced by ix_orders_cust_amt -> dropped
--       orders.fk_order_rider       replaced by ix_orders_rider_st -> dropped
--   The foreign-key CONSTRAINTS remain fully active; they are simply served by
--   the new indexes instead.
--   So "structure C = structure A + 4 indexes" is inaccurate. The report should
--   say: "4 composite/covering indexes added, 3 of which also replaced the
--   original single-column foreign-key indexes, for a net gain of 1 index."

-- Q1 Revenue per store: Store JOIN Product JOIN Order_item, aggregating
--   quantity * unit_price grouped by product_id.
--   In structure A, order_item only has a single-column index on product_id, so
--   the aggregation has to fetch quantity and price from the table.
--   This index puts all three columns in one B+ tree, so the query can be served
--   from the index alone (a covering index scan).
CREATE INDEX ix_oi_pid_cover ON order_item (product_id, quantity, unit_price);

-- Q3 Customers who bought a given product: find order_id from product_id, then
--   go back to orders to get customer_id.
--   (product_id, order_id) lets the first step complete entirely inside the index.
CREATE INDEX ix_oi_pid_oid ON order_item (product_id, order_id);

-- Orders and total spend per customer: group by customer_id and SUM(total_amount).
--   In structure A, orders only has a single-column index on customer_id, so
--   reading the amount requires a table lookup.
--   (customer_id, total_amount) lets the grouping and the sum both happen inside
--   the index.
CREATE INDEX ix_orders_cust_amt ON orders (customer_id, total_amount);

-- Deliveries per rider: Rider LEFT JOIN Orders ON rider_id AND
--   order_status <> 'cancelled', then COUNT(order_id).
--   (rider_id, order_status, order_id) lets the filter by rider, the exclusion of
--   cancelled orders and the count all happen inside the index.
CREATE INDEX ix_orders_rider_st ON orders (rider_id, order_status, order_id);

ANALYZE TABLE order_item, orders;


-- ### SECTION: revert_optimized -> C goes back to A
-- WARNING: you cannot simply DROP INDEX here. In structure C the foreign-key
-- constraints are already served by the new indexes, so a direct drop fails with:
--     ERROR 1553 (HY000): Cannot drop index 'ix_oi_pid_oid':
--                         needed in a foreign key constraint
-- The correct order is: drop the FK constraint -> drop the new index ->
-- add the FK constraint back.
--
-- IMPORTANT: the constraint names below are given EXPLICITLY. If they are omitted,
-- MySQL generates names such as orders_ibfk_1, the following drop_fk_indexes
-- section can no longer find fk_order_customer, and the whole A -> B -> A cycle
-- breaks on the second attempt. We hit exactly this during clean-room testing.

ALTER TABLE order_item DROP FOREIGN KEY fk_item_product;
ALTER TABLE orders     DROP FOREIGN KEY fk_order_customer;
ALTER TABLE orders     DROP FOREIGN KEY fk_order_rider;

DROP INDEX ix_oi_pid_cover    ON order_item;
DROP INDEX ix_oi_pid_oid      ON order_item;
DROP INDEX ix_orders_cust_amt ON orders;
DROP INDEX ix_orders_rider_st ON orders;

ALTER TABLE order_item ADD CONSTRAINT fk_item_product   FOREIGN KEY (product_id)  REFERENCES product(product_id)   ON DELETE RESTRICT ON UPDATE RESTRICT;
ALTER TABLE orders     ADD CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE RESTRICT ON UPDATE RESTRICT;
ALTER TABLE orders     ADD CONSTRAINT fk_order_rider    FOREIGN KEY (rider_id)    REFERENCES rider(rider_id)       ON DELETE RESTRICT ON UPDATE RESTRICT;

ANALYZE TABLE order_item, orders;


-- ### SECTION: drop_fk_indexes -> A becomes B
-- Builds the "no-index baseline". The FK constraint must be dropped first,
-- otherwise DROP INDEX fails with:
--   ERROR 1553 (HY000): Cannot drop index 'fk_item_product': needed in a foreign key constraint
-- Note: the foreign key on order_item.order_id REUSES the leftmost column of the
-- composite primary key, so there is no separate index for it and nothing to drop.

ALTER TABLE product   DROP FOREIGN KEY fk_product_store;
ALTER TABLE product   DROP INDEX fk_product_store;

ALTER TABLE orders    DROP FOREIGN KEY fk_order_store;
ALTER TABLE orders    DROP INDEX fk_order_store;

ALTER TABLE orders    DROP FOREIGN KEY fk_order_customer;
ALTER TABLE orders    DROP INDEX fk_order_customer;

ALTER TABLE orders    DROP FOREIGN KEY fk_order_rider;
ALTER TABLE orders    DROP INDEX fk_order_rider;

ALTER TABLE order_item DROP FOREIGN KEY fk_item_product;
ALTER TABLE order_item DROP INDEX fk_item_product;

ANALYZE TABLE product, orders, order_item;


-- ### SECTION: restore_fk_indexes -> B goes back to A
-- Adds the foreign-key constraints back. MySQL recreates the matching indexes
-- automatically, so no manual CREATE INDEX is needed.
-- The constraint names are given EXPLICITLY so that the original names
-- (fk_product_store, fk_order_store, ...) are restored. Without them MySQL would
-- generate orders_ibfk_1 and the next A -> B attempt could not find the constraint.

ALTER TABLE product    ADD CONSTRAINT fk_product_store  FOREIGN KEY (store_id)    REFERENCES store(store_id)       ON DELETE RESTRICT ON UPDATE RESTRICT;
ALTER TABLE orders     ADD CONSTRAINT fk_order_store    FOREIGN KEY (store_id)    REFERENCES store(store_id)       ON DELETE RESTRICT ON UPDATE RESTRICT;
ALTER TABLE orders     ADD CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE RESTRICT ON UPDATE RESTRICT;
ALTER TABLE orders     ADD CONSTRAINT fk_order_rider    FOREIGN KEY (rider_id)    REFERENCES rider(rider_id)       ON DELETE RESTRICT ON UPDATE RESTRICT;
ALTER TABLE order_item ADD CONSTRAINT fk_item_product   FOREIGN KEY (product_id)  REFERENCES product(product_id)   ON DELETE RESTRICT ON UPDATE RESTRICT;

ANALYZE TABLE product, orders, order_item;


-- ### SECTION: show_indexes
-- Lists every index in the current structure, for verification and for the report.

SELECT table_name, index_name,
       GROUP_CONCAT(column_name ORDER BY seq_in_index) AS cols,
       IF(non_unique = 0, 'UNIQUE', 'NON-UNIQUE')      AS kind
FROM information_schema.STATISTICS
WHERE table_schema = DATABASE()
GROUP BY table_name, index_name, non_unique
ORDER BY table_name, index_name;
