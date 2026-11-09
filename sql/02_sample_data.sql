
-- ============================================================
-- 02_sample_data.sql  --  Sample data for submission (12 orders)
-- Source: the INSERT statements of the same submitted script, kept verbatim.
-- Purpose: satisfies the brief's "sample data (screenshot only, compulsory,
--          for verification)" requirement.
--          For the performance experiment use 03_experiment_data.sql instead
--          (the scaled dataset).
-- Must be run after 01_schema.sql.
-- ============================================================
-- Sample data: 3 stores, 12 products, 6 customers, 4 riders, 12 orders, 28 items.
INSERT INTO store VALUES
(1,'Happy Fresh Market','18 Queen Road, Kowloon','852-28000001'),
(2,'Green Basket','7 Main Street, Hong Kong','852-28000002'),
(3,'Neighbour Fresh Store','25 Harbour Road, Hong Kong','852-28000003');

INSERT INTO product VALUES
(1,1,'Fresh Milk 1L',28.50,40),(2,1,'Fuji Apple',6.80,100),(3,1,'Organic Lettuce',15,25),(4,1,'Chicken Breast 500g',42,30),
(5,2,'Brown Eggs 10-pack',32,30),(6,2,'Banana 1kg',18,50),(7,2,'Carrot 500g',12.50,60),(8,2,'Greek Yogurt 500g',25,20),
(9,3,'White Rice 5kg',68,35),(10,3,'Baby Spinach 200g',22,18),(11,3,'Orange 1kg',24,45),(12,3,'Tofu 400g',14,28);

INSERT INTO customer VALUES
(1,'Chan Mei','852-61000001','Flat 3A, 10 Oak Street, Kowloon'),(2,'Wong Ho','852-61000002','Room 8, 22 Park Road, Hong Kong'),
(3,'Lee Yan','852-61000003','Unit 5, 4 River Road, Hong Kong'),(4,'Ho Ka Wai','852-61000004','Flat 12B, 9 Hill Road, Kowloon'),
(5,'Lau Sze','852-61000005','Room 2, 16 Garden Street, Hong Kong'),(6,'Tam Ming','852-61000006','Flat 7C, 31 Pine Road, Kowloon');

INSERT INTO rider VALUES
(1,'Peter Lam','852-62000001'),(2,'Amy Cheung','852-62000002'),(3,'David Ho','852-62000003'),(4,'Grace Wong','852-62000004');

INSERT INTO orders VALUES
(1,1,1,1,'2026-10-01 09:15:00',42.10,'Flat 3A, 10 Oak Street, Kowloon','2026-10-02','completed'),
(2,1,2,2,'2026-10-01 10:20:00',57,'Room 8, 22 Park Road, Hong Kong','2026-10-02','completed'),
(3,2,3,NULL,'2026-10-02 08:40:00',50,'Unit 5, 4 River Road, Hong Kong','2026-10-03','pending'),
(4,2,4,3,'2026-10-02 11:05:00',57,'Flat 12B, 9 Hill Road, Kowloon','2026-10-03','delivering'),
(5,3,5,4,'2026-10-03 15:30:00',104,'Room 2, 16 Garden Street, Hong Kong','2026-10-04','completed'),
(6,1,1,1,'2026-10-04 09:00:00',57,'Flat 3A, 10 Oak Street, Kowloon','2026-10-05','completed'),
(7,2,2,2,'2026-10-04 12:10:00',62,'Room 8, 22 Park Road, Hong Kong','2026-10-05','completed'),
(8,3,6,NULL,'2026-10-05 16:40:00',58,'Flat 7C, 31 Pine Road, Kowloon','2026-10-06','pending'),
(9,1,3,3,'2026-10-06 07:45:00',84,'Unit 5, 4 River Road, Hong Kong','2026-10-07','delivering'),
(10,2,4,4,'2026-10-06 13:25:00',43,'Flat 12B, 9 Hill Road, Kowloon','2026-10-07','pending'),
(11,3,5,1,'2026-10-07 09:35:00',50,'Room 2, 16 Garden Street, Hong Kong','2026-10-08','cancelled'),
(12,1,6,NULL,'2026-10-07 18:05:00',75.50,'Flat 7C, 31 Pine Road, Kowloon','2026-10-08','pending');

INSERT INTO order_item VALUES
(1,1,1,28.50),(1,2,2,6.80),(2,3,1,15),(2,4,1,42),(3,5,1,32),(3,6,1,18),
(4,7,1,12.50),(4,8,1,25),(4,6,1,19.50),(5,9,1,68),(5,10,1,22),(5,12,1,14),
(6,1,1,28.50),(6,3,1,15),(6,2,2,6.75),(7,5,1,32),(7,7,2,15),
(8,11,1,24),(8,12,1,14),(8,9,1,20),(9,1,2,28.50),(9,4,1,27),
(10,6,1,18),(10,8,1,25),(11,9,1,50),(12,3,1,15),(12,4,1,42),(12,2,1,18.50);
