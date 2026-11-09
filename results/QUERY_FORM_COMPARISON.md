# 老师第 4 题 · 同一查询三种写法的性能对比

> 对应查询：**买过指定商品的顾客**（老师 Topic 2 示例查询 3）
> 数据：`fresh_delivery`，5 万订单 / 150,152 条明细（结构 A 的 14 个索引）
> 测量协议：warm-up 3 次，正式测量 7 次，报告中位数

## 三种写法

| 变体 | 写法 | 来源 |
|---|---|---|
| V1 | `WHERE customer_id IN (SELECT ...)` | 提交版 `Select_Part_LUO Yipeng(4).sql` |
| V2 | `JOIN` + `DISTINCT` | 同上 |
| V3 | `WHERE EXISTS (SELECT 1 ...)` | 老师 Answer Key 第 4 题提到 `EXISTS` 半连接常优于 `IN` |

> **前提**：三种写法在每组测试中都返回**完全相同的结果集**（脚本逐组断言），
> 否则性能对比没有意义。

## 结构 A · 参考基线

### 商品 `product_id = 5`（高选择性（买家最多），买家 2182 人）

| 写法 | 中位数 (ms) | 最快 (ms) | 最慢 (ms) | 结果行数 | 与其它写法结果一致 |
|---|---:|---:|---:|---:|:--:|
| V1 IN 子查询 | 14.73 | 13.375 | 16.857 | 2182 | ✅ |
| V2 JOIN + DISTINCT | 19.806 | 18.778 | 21.413 | 2182 | ✅ |
| V3 EXISTS 半连接 | 14.391 | 13.712 | 15.972 | 2182 | ✅ |

- **V1 IN 子查询** = 基准（14.73 ms）
- **V2 JOIN + DISTINCT**：比基准**慢 1.34×**（19.806 ms）
- **V3 EXISTS 半连接**：比基准**快 1.02×**（14.391 ms）

**V1 执行计划**（商品 5）：

```text
-> Nested loop inner join  (cost=115269 rows=3375)
    -> Table scan on <subquery2>  (cost=2467..2511 rows=3375)
        -> Materialize with deduplication  (cost=2467..2467 rows=3375)
            -> Nested loop inner join  (cost=1689 rows=3375)
                -> Covering index lookup on oi using fk_item_product (product_id = 5)  (cost=377 rows=3750)
                -> Filter: (o.order_status <> 'cancelled')  (cost=0.25 rows=0.9)
                    -> Single-row index lookup on o using PRIMARY (order_id = oi.order_id)  (cost=0.25 rows=1)
    -> Single-row index lookup on c using PRIMARY (customer_id = `<subquery2>`.customer_id)  (cost=112420 rows=1)
```

### 商品 `product_id = 96`（中位选择性，买家 502 人）

| 写法 | 中位数 (ms) | 最快 (ms) | 最慢 (ms) | 结果行数 | 与其它写法结果一致 |
|---|---:|---:|---:|---:|:--:|
| V1 IN 子查询 | 4.242 | 3.827 | 5.56 | 502 | ✅ |
| V2 JOIN + DISTINCT | 4.329 | 4.102 | 4.873 | 502 | ✅ |
| V3 EXISTS 半连接 | 4.419 | 3.888 | 4.742 | 502 | ✅ |

- **V1 IN 子查询** = 基准（4.242 ms）
- **V2 JOIN + DISTINCT**：比基准**慢 1.02×**（4.329 ms）
- **V3 EXISTS 半连接**：比基准**慢 1.04×**（4.419 ms）

**V1 执行计划**（商品 96）：

```text
-> Nested loop inner join  (cost=112866 rows=526)
    -> Table scan on <subquery2>  (cost=384..393 rows=526)
        -> Materialize with deduplication  (cost=384..384 rows=526)
            -> Nested loop inner join  (cost=263 rows=526)
                -> Covering index lookup on oi using fk_item_product (product_id = 96)  (cost=58.9 rows=584)
                -> Filter: (o.order_status <> 'cancelled')  (cost=0.25 rows=0.9)
                    -> Single-row index lookup on o using PRIMARY (order_id = oi.order_id)  (cost=0.25 rows=1)
    -> Single-row index lookup on c using PRIMARY (customer_id = `<subquery2>`.customer_id)  (cost=112420 rows=1)
```

### 商品 `product_id = 194`（低选择性（买家最少），买家 340 人）

| 写法 | 中位数 (ms) | 最快 (ms) | 最慢 (ms) | 结果行数 | 与其它写法结果一致 |
|---|---:|---:|---:|---:|:--:|
| V1 IN 子查询 | 3.391 | 2.827 | 3.611 | 340 | ✅ |
| V2 JOIN + DISTINCT | 3.586 | 2.979 | 3.748 | 340 | ✅ |
| V3 EXISTS 半连接 | 3.09 | 2.763 | 3.786 | 340 | ✅ |

- **V1 IN 子查询** = 基准（3.391 ms）
- **V2 JOIN + DISTINCT**：比基准**慢 1.06×**（3.586 ms）
- **V3 EXISTS 半连接**：比基准**快 1.10×**（3.09 ms）

**V1 执行计划**（商品 194）：

```text
-> Nested loop inner join  (cost=10406 rows=361)
    -> Table scan on <subquery2>  (cost=264..271 rows=361)
        -> Materialize with deduplication  (cost=264..264 rows=361)
            -> Nested loop inner join  (cost=181 rows=361)
                -> Covering index lookup on oi using fk_item_product (product_id = 194)  (cost=40.5 rows=401)
                -> Filter: (o.order_status <> 'cancelled')  (cost=0.25 rows=0.9)
                    -> Single-row index lookup on o using PRIMARY (order_id = oi.order_id)  (cost=0.25 rows=1)
    -> Single-row index lookup on c using PRIMARY (customer_id = `<subquery2>`.customer_id)  (cost=10099 rows=1)
```


## 结构 C · 加 4 条业务索引

### 商品 `product_id = 5`（高选择性（买家最多），买家 2182 人）

| 写法 | 中位数 (ms) | 最快 (ms) | 最慢 (ms) | 结果行数 | 与其它写法结果一致 |
|---|---:|---:|---:|---:|:--:|
| V1 IN 子查询 | 15.027 | 14.101 | 18.955 | 2182 | ✅ |
| V2 JOIN + DISTINCT | 20.111 | 19.008 | 20.805 | 2182 | ✅ |
| V3 EXISTS 半连接 | 14.739 | 14.218 | 15.48 | 2182 | ✅ |

- **V1 IN 子查询** = 基准（15.027 ms）
- **V2 JOIN + DISTINCT**：比基准**慢 1.34×**（20.111 ms）
- **V3 EXISTS 半连接**：比基准**快 1.02×**（14.739 ms）

**V1 执行计划**（商品 5）：

```text
-> Nested loop inner join  (cost=115004 rows=3375)
    -> Table scan on <subquery2>  (cost=2470..2514 rows=3375)
        -> Materialize with deduplication  (cost=2470..2470 rows=3375)
            -> Nested loop inner join  (cost=1692 rows=3375)
                -> Covering index lookup on oi using ix_oi_pid_oid (product_id = 5)  (cost=379 rows=3750)
                -> Filter: (o.order_status <> 'cancelled')  (cost=0.25 rows=0.9)
                    -> Single-row index lookup on o using PRIMARY (order_id = oi.order_id)  (cost=0.25 rows=1)
    -> Single-row index lookup on c using PRIMARY (customer_id = `<subquery2>`.customer_id)  (cost=112152 rows=1)
```

### 商品 `product_id = 96`（中位选择性，买家 502 人）

| 写法 | 中位数 (ms) | 最快 (ms) | 最慢 (ms) | 结果行数 | 与其它写法结果一致 |
|---|---:|---:|---:|---:|:--:|
| V1 IN 子查询 | 4.299 | 4.056 | 5.136 | 502 | ✅ |
| V2 JOIN + DISTINCT | 4.474 | 4.248 | 5.143 | 502 | ✅ |
| V3 EXISTS 半连接 | 4.198 | 4.161 | 4.605 | 502 | ✅ |

- **V1 IN 子查询** = 基准（4.299 ms）
- **V2 JOIN + DISTINCT**：比基准**慢 1.04×**（4.474 ms）
- **V3 EXISTS 半连接**：比基准**快 1.02×**（4.198 ms）

**V1 执行计划**（商品 96）：

```text
-> Nested loop inner join  (cost=112599 rows=526)
    -> Table scan on <subquery2>  (cost=385..394 rows=526)
        -> Materialize with deduplication  (cost=385..385 rows=526)
            -> Nested loop inner join  (cost=264 rows=526)
                -> Covering index lookup on oi using ix_oi_pid_cover (product_id = 96)  (cost=59.5 rows=584)
                -> Filter: (o.order_status <> 'cancelled')  (cost=0.25 rows=0.9)
                    -> Single-row index lookup on o using PRIMARY (order_id = oi.order_id)  (cost=0.25 rows=1)
    -> Single-row index lookup on c using PRIMARY (customer_id = `<subquery2>`.customer_id)  (cost=112152 rows=1)
```

### 商品 `product_id = 194`（低选择性（买家最少），买家 340 人）

| 写法 | 中位数 (ms) | 最快 (ms) | 最慢 (ms) | 结果行数 | 与其它写法结果一致 |
|---|---:|---:|---:|---:|:--:|
| V1 IN 子查询 | 3.164 | 2.978 | 3.602 | 340 | ✅ |
| V2 JOIN + DISTINCT | 3.443 | 3.101 | 3.636 | 340 | ✅ |
| V3 EXISTS 半连接 | 3.281 | 2.816 | 3.558 | 340 | ✅ |

- **V1 IN 子查询** = 基准（3.164 ms）
- **V2 JOIN + DISTINCT**：比基准**慢 1.09×**（3.443 ms）
- **V3 EXISTS 半连接**：比基准**慢 1.04×**（3.281 ms）

**V1 执行计划**（商品 194）：

```text
-> Nested loop inner join  (cost=10403 rows=361)
    -> Table scan on <subquery2>  (cost=265..272 rows=361)
        -> Materialize with deduplication  (cost=265..265 rows=361)
            -> Nested loop inner join  (cost=181 rows=361)
                -> Covering index lookup on oi using ix_oi_pid_cover (product_id = 194)  (cost=41 rows=401)
                -> Filter: (o.order_status <> 'cancelled')  (cost=0.25 rows=0.9)
                    -> Single-row index lookup on o using PRIMARY (order_id = oi.order_id)  (cost=0.25 rows=1)
    -> Single-row index lookup on c using PRIMARY (customer_id = `<subquery2>`.customer_id)  (cost=10096 rows=1)
```

