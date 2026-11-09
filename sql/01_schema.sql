-- ============================================================
-- 01_schema.sql  --  Table creation script (DDL)
-- Source: the DDL part of the table-creation script submitted by a group
--         member, kept verbatim with no modifications.
-- Target DBMS: MySQL Community Server 8.0.46
-- Run order: 01_schema.sql -> 02_sample_data.sql
--            (the performance experiment uses 03_experiment_data.sql instead)
-- Note: this script assumes the target database already exists and is selected;
--       the group uses the database name group_project
-- ============================================================
-- MySQL 8.0+. Select the target schema before running.
-- CREATE DATABASE group_project;
-- USE group_project;

SET FOREIGN_KEY_CHECKS=0;
DROP TABLE IF EXISTS order_item;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS product;
DROP TABLE IF EXISTS rider;
DROP TABLE IF EXISTS customer;
DROP TABLE IF EXISTS store;
SET FOREIGN_KEY_CHECKS=1;

CREATE TABLE store (
 store_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 store_name VARCHAR(60) NOT NULL,
 address VARCHAR(200) NOT NULL,
 phone VARCHAR(20) NOT NULL,
 
 CONSTRAINT uq_store_phone UNIQUE(phone)
) ENGINE=InnoDB;

CREATE TABLE product (
 product_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 store_id INT UNSIGNED NOT NULL,
 product_name VARCHAR(80) NOT NULL,
 price DECIMAL(8,2) NOT NULL,
 stock_quantity INT NOT NULL,
 
 CONSTRAINT ck_product_price CHECK(price>=0),
 CONSTRAINT ck_product_stock CHECK(stock_quantity>=0),
 CONSTRAINT fk_product_store FOREIGN KEY(store_id) REFERENCES store(store_id)
   ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE customer (
 customer_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 customer_name VARCHAR(40) NOT NULL,
 phone VARCHAR(20) NOT NULL,
 default_address VARCHAR(200) NOT NULL,
 
 CONSTRAINT uq_customer_phone UNIQUE(phone)
) ENGINE=InnoDB;

CREATE TABLE rider (
 rider_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 rider_name VARCHAR(40) NOT NULL,
 phone VARCHAR(20) NOT NULL,
 
 CONSTRAINT uq_rider_phone UNIQUE(phone)
) ENGINE=InnoDB;

CREATE TABLE orders (
 order_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 store_id INT UNSIGNED NOT NULL,
 customer_id INT UNSIGNED NOT NULL,
 rider_id INT UNSIGNED NULL,
 order_time DATETIME NOT NULL,
 total_amount DECIMAL(10,2) NOT NULL,
 delivery_address VARCHAR(200) NOT NULL,
 delivery_date DATE NOT NULL,
 order_status VARCHAR(20) NOT NULL,

 CONSTRAINT ck_order_total CHECK(total_amount>=0),
 CONSTRAINT ck_order_status CHECK(order_status IN('pending','delivering','completed','cancelled')),
 CONSTRAINT fk_order_store FOREIGN KEY(store_id) REFERENCES store(store_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 CONSTRAINT fk_order_customer FOREIGN KEY(customer_id) REFERENCES customer(customer_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 CONSTRAINT fk_order_rider FOREIGN KEY(rider_id) REFERENCES rider(rider_id) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE order_item (
 order_id INT UNSIGNED NOT NULL,
 product_id INT UNSIGNED NOT NULL,
 quantity INT NOT NULL,
 unit_price DECIMAL(8,2) NOT NULL,
 
 CONSTRAINT pk_order_item PRIMARY KEY(order_id,product_id),
 CONSTRAINT ck_item_quantity CHECK(quantity>0),
 CONSTRAINT ck_item_unit_price CHECK(unit_price>=0),
 CONSTRAINT fk_item_order FOREIGN KEY(order_id) REFERENCES orders(order_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 CONSTRAINT fk_item_product FOREIGN KEY(product_id) REFERENCES product(product_id) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;
