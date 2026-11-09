# Topic 2 社区生鲜次日达 · 性能实验结果表

> 生成时间：2026-10-13 15:27:06
> 被测量查询取自 `Select_Part_LUO Yipeng(4).sql`（提交版）

## 表 A 测试环境

| 项目 | 值 |
|---|---|
| DBMS（服务器） | MySQL Community Server 8.0.46 for Win64 on x86_64 |
| 存储引擎 | InnoDB |
| innodb_buffer_pool_size | 134217728 (128 MiB) |
| innodb_flush_log_at_trx_commit | 1 |
| 隔离级别 | REPEATABLE-READ |
| Windows 服务名 / 端口 | MySQL / 127.0.0.1:3306 |
| 客户端 | Python mysql.connector，单连接单线程 |
| 测量协议 | 每条查询 warm-up 3 次，正式测量 7 次，报告中位 |

## 表 B 数据集规模

| 表 | 行数 | 说明 |
|---|---:|---|
| `store` | 20 | 20 家门店，订单量呈头部效应 |
| `product` | 200 | 200 个商品（每店 10 个），其中 20 个从未售出 |
| `customer` | 5,000 | 5000 位顾客，其中 500 位从未下单 |
| `rider` | 200 | 200 位骑手，其中 20 位从未配送 |
| `orders` | 50,000 | 约 15% 尚未派单；状态与订单新旧相关 |
| `order_item` | 150,152 | 每单 1–5 条，商品必定与订单同店 |

> 数据为**合成数据**（无真实运营数据可用）。生成脚本 `03_experiment_data.sql`。
> 伪随机来自 `SHA2()` 哈希而非 `RAND()`，重复执行可得到完全相同的数据集。

## 表 C 三种结构下的核心查询表现

| 查询 | A 基线 (ms) | C 加索引 (ms) | C 相对 A | B 无索引 (ms) | B 相对 A | A 访问计划 | C 访问计划 |
|---|---:|---:|---:|---:|---:|---|---|
| Q1 门店销售额（经 order_item 汇总） | 705.215 | 463.641 | 1.5x 快 | 1037.914 | 1.5x 慢 | s:ALL(20) → p:ref(10) → oi:ref(892) → o:eq_ref(1) | s:ALL(20) → p:ref(10) → oi:ref(804) → o:eq_ref(1) |
| Q2 每位骑手配送量（含零单骑手） | 118.042 | 40.036 | 2.9x 快 | 562.765 | 4.8x 慢 | r:ALL(200) → o:ref(269) | r:ALL(200) → o:ref(274) |
| Q3 买过指定商品的顾客（子查询版） | 14.785 | 15.029 | 1.02x 慢 | 45.302 | 3.1x 慢 | <subquery2>:ALL(None) → customer:eq_ref(1) → oi:ref(3661) → o:eq_ref(1) | <subquery2>:ALL(None) → customer:eq_ref(1) → oi:ref(3661) → o:eq_ref(1) |
| Q3' 买过指定商品的顾客（JOIN 版） | 19.271 | 20.587 | 1.07x 慢 | 49.616 | 2.6x 慢 | oi:ref(3661) → o:eq_ref(1) → c:eq_ref(1) | oi:ref(3661) → o:eq_ref(1) → c:eq_ref(1) |
| Q4 每位顾客订单数与消费总额 | 168.859 | 156.723 | 1.1x 快 | 220.456 | 1.3x 慢 | c:ALL(5021) → o:ref(11) | c:ALL(5021) → o:ref(11) |
| Q5 尚未派单的订单 | 33.743 | 33.059 | 1.0x 快 | 37.793 | 1.1x 慢 | orders:ref(7507) | orders:ref(7507) |

> **访问计划写法**：`表:访问类型(估算行数)`，取自 `EXPLAIN FORMAT=TRADITIONAL`。
> `ALL` = 全表扫描；`ref` / `eq_ref` / `index` = 使用索引；带 `Using index` 表示覆盖索引，无需回表。

### 执行计划对比（结构 A vs C，Q1 门店销售额）

> 注：下表的结构化字段取自 `EXPLAIN FORMAT=TRADITIONAL`，表格格式便于逐列比较。

**A 基线** — 传统表格：

| 表 | 访问类型 | 使用索引 | 估算行数 | 附加信息 |
|---|---|---|---:|---|
| `s` | ALL | - | 20 | Using temporary; Using filesort |
| `p` | ref | fk_product_store | 10 | Using index |
| `oi` | ref | fk_item_product | 892 | - |
| `o` | eq_ref | PRIMARY | 1 | - |

**A 基线** — 树形计划（`EXPLAIN` 默认输出）：

```text
-> Sort: sales_amount DESC
    -> Table scan on <temporary>
        -> Aggregate using temporary table
            -> Nested loop left join  (cost=125001 rows=178534)
                -> Nested loop left join  (cost=62514 rows=178534)
                    -> Nested loop left join  (cost=27.3 rows=200)
                        -> Table scan on s  (cost=2.25 rows=20)
                        -> Covering index lookup on p using fk_product_store (store_id = s.store_id)  (cost=0.302 rows=10)
                    -> Index lookup on oi using fk_item_product (product_id = p.product_id)  (cost=224 rows=893)
                -> Single-row index lookup on o using PRIMARY (order_id = oi.order_id)  (cost=0.25 rows=1)
```

**C 加索引** — 传统表格：

| 表 | 访问类型 | 使用索引 | 估算行数 | 附加信息 |
|---|---|---|---:|---|
| `s` | ALL | - | 20 | Using temporary; Using filesort |
| `p` | ref | fk_product_store | 10 | Using index |
| `oi` | ref | ix_oi_pid_cover | 804 | Using index |
| `o` | eq_ref | PRIMARY | 1 | - |

**C 加索引** — 树形计划（`EXPLAIN` 默认输出）：

```text
-> Sort: sales_amount DESC
    -> Table scan on <temporary>
        -> Aggregate using temporary table
            -> Nested loop left join  (cost=72618 rows=160983)
                -> Nested loop left join  (cost=16274 rows=160983)
                    -> Nested loop left join  (cost=27.3 rows=200)
                        -> Table scan on s  (cost=2.25 rows=20)
                        -> Covering index lookup on p using fk_product_store (store_id = s.store_id)  (cost=0.302 rows=10)
                    -> Covering index lookup on oi using ix_oi_pid_cover (product_id = p.product_id)  (cost=1.14 rows=805)
                -> Single-row index lookup on o using PRIMARY (order_id = oi.order_id)  (cost=0.25 rows=1)
```


## 表 D 写入与存储代价

| 指标 | A 基线 | C 加索引 | B 无索引 |
|---|---:|---:|---:|
| `orders` + `order_item` 索引总数 | 6 | 7 | 2 |
| 批量插入 150,000 行明细耗时中位数 (s) | 1.414 | 1.908 | 1.057 |
| 写入耗时相对 A 的变化 | — | +34.9% | -25.2% |
| 全库索引占用 (MB) | 8.27 | 11.78 | 0.18 |

### 每张表的空间占用（结构 A）

| 表 | 数据 (MB) | 索引 (MB) | 合计 (MB) |
|---|---:|---:|---:|
| `customer` | 0.45 | 0.14 | 0.59 |
| `order_item` | 7.52 | 3.52 | 11.03 |
| `orders` | 5.52 | 4.55 | 10.06 |
| `product` | 0.02 | 0.02 | 0.03 |
| `rider` | 0.02 | 0.02 | 0.03 |
| `store` | 0.02 | 0.02 | 0.03 |

### 索引清单（结构 A，共 14 个）

| 表 | 索引 | 列 |
|---|---|---|
| `customer` | `PRIMARY` | customer_id |
| `customer` | `uq_customer_phone` | phone |
| `order_item` | `fk_item_product` | product_id |
| `order_item` | `PRIMARY` | order_id,product_id |
| `orders` | `fk_order_customer` | customer_id |
| `orders` | `fk_order_rider` | rider_id |
| `orders` | `fk_order_store` | store_id |
| `orders` | `PRIMARY` | order_id |
| `product` | `fk_product_store` | store_id |
| `product` | `PRIMARY` | product_id |
| `rider` | `PRIMARY` | rider_id |
| `rider` | `uq_rider_phone` | phone |
| `store` | `PRIMARY` | store_id |
| `store` | `uq_store_phone` | phone |

### 结构 C 新增的 4 条索引

| 索引 | 列 | 目标查询 |
|---|---|---|
| `ix_oi_pid_cover` | order_item(product_id, quantity, unit_price) | Q1 门店销售额 |
| `ix_oi_pid_oid` | order_item(product_id, order_id) | Q3 买过指定商品的顾客 |
| `ix_orders_cust_amt` | orders(customer_id, total_amount) | Q4 每位顾客订单数与消费总额 |
| `ix_orders_rider_st` | orders(rider_id, order_status, order_id) | Q2 每位骑手配送量 |

> ⚠️ **本次实验的一个实测发现（值得单独写进报告）**：
> MySQL 在新索引能够替代外键自动索引时，会**自动删除原来的外键单列索引**。
> 因此在结构 A 上执行上述 4 条 `CREATE INDEX` 后，索引总数由 14 变为 15（而不是 14+4=18）：
> `order_item.fk_item_product`、`orders.fk_order_customer`、`orders.fk_order_rider` 三条单列外键索引被对应的复合索引取代并删除；外键**约束**本身仍然有效。
> 净效果是**新增 4 条复合索引、移除 3 条单列索引，净增 1 个索引**。
> 这也意味着回退时不能直接 `DROP INDEX`（会报 `ERROR 1553`），必须先删外键约束、再删索引、最后把外键加回来 —— 见 `04_indexes.sql` 的 `revert_optimized` 段。
