USE group_project;

-- Query all stores
SELECT
    store_id,
    store_name,
    address,
    phone
FROM store;

-- Query all products and their respective stores
SELECT
    p.product_id,
    p.product_name,
    p.price,
    p.stock_quantity,
    s.store_name
FROM product p
JOIN store s
    ON p.store_id = s.store_id;
    
-- Query the product catalog of a specific store(eg. store_id = 1)
SELECT
    p.product_id,
    p.product_name,
    p.price,
    p.stock_quantity
FROM product p
WHERE p.store_id = 1;

-- Check for goods that are out of stock(eg. any item with less than 10 units requires restocking)
SELECT
    p.product_id,
    p.product_name,
    s.store_name,
    p.stock_quantity
FROM product p
JOIN store s
    ON p.store_id = s.store_id
WHERE p.stock_quantity < 10
ORDER BY p.stock_quantity ASC;

-- Check for out-of-stock items
SELECT
    product_id,
    product_name,
    stock_quantity
FROM product
WHERE stock_quantity = 0;

-- Search for products with prices ranging from 20 to 100
SELECT
    product_id,
    product_name,
    price
FROM product
WHERE price BETWEEN 20 AND 100
ORDER BY price ASC;

-- Perform a fuzzy search based on the product name
SELECT
    product_id,
    product_name,
    price,
    stock_quantity
FROM product
WHERE product_name LIKE '%Milk%';

-- Query the quantity of goods for each store
SELECT
    s.store_id,
    s.store_name,
    COUNT(p.product_id) AS product_count
FROM store s
LEFT JOIN product p
    ON s.store_id = p.store_id
GROUP BY s.store_id, s.store_name;

-- Query the average price of goods for each store
SELECT
    s.store_id,
    s.store_name,
    AVG(p.price) AS average_price
FROM store s
JOIN product p
    ON s.store_id = p.store_id
GROUP BY s.store_id, s.store_name;

-- Query the most expensive product for each store
SELECT
    s.store_name,
    MAX(p.price) AS highest_price
FROM store s
JOIN product p
    ON s.store_id = p.store_id
GROUP BY s.store_id, s.store_name;

-- Query all customers
SELECT
    customer_id,
    customer_name,
    phone,
    default_address
FROM customer;

-- Query customer information based on the mobile phone number
SELECT
    customer_id,
    customer_name,
    phone,
    default_address
FROM customer
WHERE phone = '852-61000001';

-- Query the number of orders and the total consumption amount of the customer
SELECT
    c.customer_id,
    c.customer_name,
    COUNT(o.order_id) AS order_count,
    COALESCE(SUM(o.total_amount), 0) AS total_spending
FROM customer c
LEFT JOIN orders o
    ON c.customer_id = o.customer_id
    AND o.order_status <> 'cancelled'
GROUP BY c.customer_id, c.customer_name;

-- Query the customer with the highest consumption amount
SELECT
    c.customer_id,
    c.customer_name,
    SUM(o.total_amount) AS total_spending
FROM customer c
JOIN orders o
    ON c.customer_id = o.customer_id
    WHERE o.order_status <> 'cancelled'
GROUP BY c.customer_id, c.customer_name
ORDER BY total_spending DESC
LIMIT 10;

-- Query all orders
SELECT
    order_id,
    store_id,
    customer_id,
    rider_id,
    order_time,
    total_amount,
    delivery_address,
    delivery_date,
    order_status
FROM orders
ORDER BY order_time DESC;

-- Query the details of the order, including the customer, the store and the rider
SELECT
    o.order_id,
    o.order_time,
    s.store_name,
    c.customer_name,
    c.phone AS customer_phone,
    r.rider_name,
    r.phone AS rider_phone,
    o.total_amount,
    o.delivery_address,
    o.delivery_date,
    o.order_status
FROM orders o
JOIN store s
    ON o.store_id = s.store_id
JOIN customer c
    ON o.customer_id = c.customer_id
LEFT JOIN rider r
    ON o.rider_id = r.rider_id
ORDER BY o.order_time DESC;

-- Check pending orders
SELECT
    o.order_id,
    o.order_time,
    s.store_name,
    c.customer_name,
    c.phone,
    o.total_amount,
    o.delivery_address
FROM orders o
JOIN store s
    ON o.store_id = s.store_id
JOIN customer c
    ON o.customer_id = c.customer_id
WHERE o.order_status = 'pending'
ORDER BY o.order_time ASC;

-- Query the orders that are currently being delivered
SELECT
    o.order_id,
    c.customer_name,
    r.rider_name,
    r.phone AS rider_phone,
    o.delivery_address,
    o.delivery_date
FROM orders o
JOIN customer c
    ON o.customer_id = c.customer_id
JOIN rider r
    ON o.rider_id = r.rider_id
WHERE o.order_status = 'delivering';

-- Query completed orders
SELECT
    order_id,
    customer_id,
    total_amount,
    delivery_date
FROM orders
WHERE order_status = 'completed'
ORDER BY delivery_date DESC;

-- Check cancelled orders
SELECT
    order_id,
    customer_id,
    total_amount,
    order_time,
    order_status
FROM orders
WHERE order_status = 'cancelled';

-- Check today's orders
SELECT
    order_id,
    customer_id,
    total_amount,
    order_status
FROM orders
WHERE order_time >= CURDATE()
  AND order_time < CURDATE() + INTERVAL 1 DAY;
  
-- Orders with higher transaction amounts
SELECT
    order_id,
    customer_id,
    total_amount,
    order_time
FROM orders
WHERE total_amount >= 80
ORDER BY total_amount DESC;

-- Orders that have not assigned a rider yet
SELECT
    order_id,
    customer_id,
    store_id,
    order_time,
    order_status
FROM orders
WHERE rider_id IS NULL;

-- Query orders whose delivery dates have already exceeded the deadline
SELECT
    order_id,
    customer_id,
    delivery_date,
    order_status
FROM orders
WHERE delivery_date < CURDATE()
  AND order_status NOT IN ('completed', 'cancelled');
  
-- Query all the items in a certain order
SELECT
    oi.order_id,
    p.product_id,
    p.product_name,
    oi.quantity,
    oi.unit_price,
    oi.quantity * oi.unit_price AS item_amount
FROM order_item oi
JOIN product p
    ON oi.product_id = p.product_id
WHERE oi.order_id = 1;

-- Query all order details
SELECT
    oi.order_id,
    p.product_name,
    oi.quantity,
    oi.unit_price,
    oi.quantity * oi.unit_price AS item_amount
FROM order_item oi
JOIN product p
    ON oi.product_id = p.product_id
ORDER BY oi.order_id;

-- Query the quantity of each type of goods for each order
SELECT
    o.order_id,
    o.total_amount,
    COUNT(oi.product_id) AS product_type_count
FROM orders o
LEFT JOIN order_item oi
    ON o.order_id = oi.order_id
GROUP BY o.order_id, o.total_amount;

-- Query the total quantity of goods for each order
SELECT
    oi.order_id,
    SUM(oi.quantity) AS total_quantity
FROM order_item oi
GROUP BY oi.order_id;

-- Query the details of the order amount and the total order amount
SELECT
    o.order_id,
    o.total_amount AS recorded_total,
    SUM(oi.quantity * oi.unit_price) AS calculated_total,
    SUM(oi.quantity * oi.unit_price) - o.total_amount AS difference
FROM orders o
JOIN order_item oi
    ON o.order_id = oi.order_id
GROUP BY o.order_id, o.total_amount;

-- Query the product with the highest purchase quantity
SELECT
    p.product_id,
    p.product_name,
    SUM(oi.quantity) AS total_sold_quantity
FROM order_item oi
JOIN product p
    ON oi.product_id = p.product_id
JOIN orders o
    ON oi.order_id = o.order_id
WHERE o.order_status <> 'cancelled'
GROUP BY p.product_id, p.product_name
ORDER BY total_sold_quantity DESC
LIMIT 10;

-- Query the product with the highest sales volume
SELECT
    p.product_id,
    p.product_name,
    SUM(oi.quantity * oi.unit_price) AS sales_amount
FROM order_item oi
JOIN product p
    ON oi.product_id = p.product_id
JOIN orders o
    ON oi.order_id = o.order_id
WHERE o.order_status <> 'cancelled'
GROUP BY p.product_id, p.product_name
ORDER BY sales_amount DESC
LIMIT 10;

-- Query all riders and the quantity of delivery orders
SELECT
    r.rider_id,
    r.rider_name,
    r.phone,
    COUNT(o.order_id) AS delivery_count
FROM rider r
LEFT JOIN orders o
    ON r.rider_id = o.rider_id
   AND o.order_status <> 'cancelled'
GROUP BY r.rider_id, r.rider_name, r.phone;

-- Query the rider who has the most delivery orders
SELECT
    r.rider_id,
    r.rider_name,
    COUNT(o.order_id) AS delivery_count
FROM rider r
JOIN orders o
    ON r.rider_id = o.rider_id
WHERE o.order_status <> 'cancelled'
GROUP BY r.rider_id, r.rider_name
ORDER BY delivery_count DESC
LIMIT 1;

-- Query the current orders being delivered by a certain rider
SELECT
    o.order_id,
    c.customer_name,
    c.phone,
    o.delivery_address,
    o.delivery_date
FROM orders o
JOIN customer c
    ON o.customer_id = c.customer_id
WHERE o.rider_id = 3
  AND o.order_status = 'delivering';

-- Query the store with the highest sales volume
SELECT
    s.store_id,
    s.store_name,
    SUM(o.total_amount) AS sales_amount
FROM store s
JOIN orders o
    ON s.store_id = o.store_id
WHERE o.order_status <> 'cancelled'
GROUP BY s.store_id, s.store_name
ORDER BY sales_amount DESC
LIMIT 1;

-- Query the daily sales figures
SELECT
    DATE(order_time) AS order_date,
    COUNT(order_id) AS order_count,
    SUM(total_amount) AS daily_sales
FROM orders
WHERE order_status <> 'cancelled'
GROUP BY DATE(order_time)
ORDER BY order_date DESC;

-- Query the monthly sales figures
SELECT
    YEAR(order_time) AS order_year,
    MONTH(order_time) AS order_month,
    COUNT(order_id) AS order_count,
    SUM(total_amount) AS monthly_sales
FROM orders
WHERE order_status <> 'cancelled'
GROUP BY YEAR(order_time), MONTH(order_time)
ORDER BY order_year DESC, order_month DESC;

-- Query the customers who have purchased a certain product
SELECT DISTINCT
    c.customer_id,
    c.customer_name,
    c.phone
FROM customer c
JOIN orders o
    ON c.customer_id = o.customer_id
JOIN order_item oi
    ON o.order_id = oi.order_id
WHERE oi.product_id = 1
  AND o.order_status <> 'cancelled';
-- Query the most sold product for each store
WITH product_sales AS (
    SELECT
        p.store_id,
        p.product_id,
        p.product_name,
        SUM(oi.quantity) AS total_sold_quantity,
        RANK() OVER (
            PARTITION BY p.store_id
            ORDER BY SUM(oi.quantity) DESC
        ) AS ranking
    FROM product p
    JOIN order_item oi
        ON p.product_id = oi.product_id
    JOIN orders o
        ON oi.order_id = o.order_id
    WHERE o.order_status <> 'cancelled'
    GROUP BY
        p.store_id,
        p.product_id,
        p.product_name
)
SELECT
    s.store_name,
    ps.product_name,
    ps.total_sold_quantity
FROM product_sales ps
JOIN store s
    ON ps.store_id = s.store_id
WHERE ps.ranking = 1;

-- Query order status statistics
SELECT
    order_status,
    COUNT(*) AS order_count,
    SUM(total_amount) AS total_amount
FROM orders
GROUP BY order_status;

-- Query cancellation rate
SELECT
    COUNT(CASE WHEN order_status = 'cancelled' THEN 1 END)
        / COUNT(*) * 100 AS cancellation_rate
FROM orders;

-- Query the cancellation rates of each store
SELECT
    s.store_id,
    s.store_name,
    COUNT(CASE WHEN o.order_status = 'cancelled' THEN 1 END)
        / COUNT(o.order_id) * 100 AS cancellation_rate
FROM store s
JOIN orders o
    ON s.store_id = o.store_id
GROUP BY s.store_id, s.store_name;

-- Customers with at least 3 orders
SELECT
    c.customer_id,
    c.customer_name,
    COUNT(o.order_id) AS order_count,
    SUM(o.total_amount) AS total_spending
FROM customer c
JOIN orders o
    ON c.customer_id = o.customer_id
WHERE o.order_status <> 'cancelled'
GROUP BY c.customer_id, c.customer_name
HAVING COUNT(o.order_id) >= 3
ORDER BY order_count DESC;

-- Query customers who have purchased a specific product
SELECT
    customer_id,
    customer_name,
    phone
FROM customer
WHERE customer_id IN (
    SELECT o.customer_id
    FROM orders o
    JOIN order_item oi
        ON o.order_id = oi.order_id
    WHERE oi.product_id = 1
      AND o.order_status <> 'cancelled'
);

-- Query customers who have never placed an order
SELECT
    c.customer_id,
    c.customer_name,
    c.phone
FROM customer c
WHERE NOT EXISTS (
    SELECT 1
    FROM orders o
    WHERE o.customer_id = c.customer_id
);

-- Search for goods that have never been sold
SELECT
    p.product_id,
    p.product_name,
    p.stock_quantity
FROM product p
WHERE NOT EXISTS (
    SELECT 1
    FROM order_item oi
    JOIN orders o
        ON oi.order_id = o.order_id
    WHERE oi.product_id = p.product_id
      AND o.order_status <> 'cancelled'
);

-- Calculate the sales of the store based on the order details
SELECT
    s.store_id,
    s.store_name,
    COALESCE(SUM(CASE WHEN o.order_status <> 'cancelled'
                      THEN oi.quantity * oi.unit_price END), 0) AS sales_amount
FROM store s
LEFT JOIN product p
    ON s.store_id = p.store_id
LEFT JOIN order_item oi
    ON p.product_id = oi.product_id
LEFT JOIN orders o
    ON oi.order_id = o.order_id
GROUP BY
    s.store_id,
    s.store_name
ORDER BY sales_amount DESC;