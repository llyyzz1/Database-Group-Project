# CDS 534 小组项目 · Topic 2 社区生鲜次日达 · 数据库工程

> 课程：CDS 534 Database Management — Group Project: Design a Real-World Database
> 主题：Topic 2 Community Fresh-Food Next-Day Delivery
> 截止：2026-11-12 20:00

---

## 目录结构

```text
project/
  sql/
    00_build_experiment_database.sql  一键：建库 + 建表 + 生成放大数据集
    01_schema.sql             建表脚本（DDL）—— 组员提交版，原样保留
    02_sample_data.sql        提交用样例数据（3 门店 / 12 商品 / 12 订单 / 28 明细）
    03_experiment_data.sql    性能实验用放大数据集（合成，5 万订单 / 15 万明细）
    04_indexes.sql            索引实验：结构 A / B / C 的切换与回退
    索引使用说明.md             ★ 索引清单、设计理由、实测收益、切换步骤、错误码对照
    queries_submitted.sql     组员提交的 48 条查询（基准测试从中自动提取）
  results/
    05_benchmark.py                 基准测试：3 种结构 × 6 条核心查询 + 写入代价
    06_query_form_comparison.py     老师第 4 题：IN 子查询 / JOIN / EXISTS 三种写法对比
    07_acid_experiment.py           老师第 5 题：ACID 与并发一致性实测
    08_make_figures.py              生成报告用图表（SVG 矢量 + PNG 300dpi）
    阈值.md                          ★ 可衡量设计目标与阈值（第 3 节 + 第 8 节达标依据）
    RESULT_TABLES.md                ★ 4 张结果表，可直接放进报告第 8 节
    QUERY_FORM_COMPARISON.md        ★ 老师第 4 题的实测答案
    ACID_EVIDENCE.md                ★ 老师第 5 题与一致性权衡的实测证据
    Q1_Q2_Q3_Q7_Q8_demo_output.txt  第 1/2/3/7/8 题的实测演示输出
    sample_data_dump.json           从 group_project 导出的样例数据（截图来源）
    figures/                        ★ 两张报告图（fig1 查询性能、fig2 写入与空间代价）
    all_results.json                全部原始数据
    A_reference_baseline/           结构 A 原始测量结果
    C_optimized/                    结构 C 原始测量结果
    B_no_index/                     结构 B 原始测量结果
  diagrams/                        ★ 交付图表
    ER_diagram_Topic2.svg             矢量 ER 图（插报告用这个）
    ER_diagram_Topic2.png             预览
    sample_data_1_master_tables.png   样例数据截图（主数据表）
    sample_data_2_orders.png          样例数据截图（订单）
    sample_data_3_order_items.png     样例数据截图（明细）
  report/                          ★ 报告章节草稿（Word）
    Section8_Evaluation_and_Conclusions.docx      第 8 节英文版
    第8节_评价与设计权衡_中文版.docx                 第 8 节中文版
    Section9_SQL_Theory_Questions_All8.docx       第 9 节：8 道题完整版
  _archive/                        已被取代的旧版本（不参与交付）
  README.md                        本文件
```

---

## 交付图表（diagrams/）

老师要求的两项硬性交付物都在 `diagrams/` 里：

| 文件 | 对应要求 | 说明 |
|---|---|---|
| `ER_diagram_Topic2.svg` | `ER diagram (vector graphic or in-document drawing) (compulsory)` | **矢量图**，插入 Word 后放大不糊 |
| `ER_diagram_Topic2.png` | — | 同图位图预览 |
| `sample_data_1_master_tables.png` | `sample data (screenshot only, compulsory, for verification)` | store / product / customer / rider |
| `sample_data_2_orders.png` | 同上 | orders 12 单 |
| `sample_data_3_order_items.png` | 同上 | order_item 28 条 |

**ER 图相对组员初版修正了 7 处**（详见 `../小组SQL文件汇总/README.md`）：
改为矢量、删除建表脚本里没有的 3 个 `*_status` 列、补标 2 个 `UNIQUE`、标出 `rider_id` 可空、
修正 `Appares_in` 拼写、删除有歧义的 `(min,max)`、加注 N:M 如何经 Order_item 拆解。

**一致性已验证**：脚本 `tools/verify_er_matches_ddl.py` 逐列比对，6 实体 / 29 属性 /
可空性 / 6 个外键标记全部与建表脚本一致。

---

## 运行方式

### 文件编码与注释语言

**`sql/` 下的 6 个 `.sql` 文件：注释全部是英文，编码为 UTF-8 with BOM。**

#### 为什么注释改成了英文

原先注释是中文，但在 MySQL Workbench 里显示成**空心方框（豆腐块）**。排查结论：

- 文件编码**没有错**（已用 `utf-8` 严格解码验证，中文字符码位正确）
- 根因是 **Workbench 的编辑器字体**。其配置为
  `workbench.general.Editor:Font = Consolas 10`，而 **Consolas 不含中文字形**，
  Workbench 的编辑器（基于 Scintilla）在 Windows 上不做字体回退，于是中文全部变成方框。
- 典型判据：同一行里 ASCII 正常显示（`MySQL Workbench`、`WHERE`、`total_amount` 等），
  只有中文变方框。若是编码错误，中文会变成拉丁乱码（如 `ç”¨é€”`）且字符数会变化。

**根治办法是把注释改成英文**（本仓库已全部改完），这样任何字体、任何编码设置下都不会出问题；
顺带也更适合交给英文课程。

如果你仍想在 Workbench 里看中文（比如看本 README 或 `索引使用说明.md`），
把编辑器字体换掉即可：`Edit` → `Preferences` → `Fonts & Colors` → `Editor Font`
改成 **NSimSun**（新宋体，等宽且有中文字形）或 微软雅黑。

#### 为什么仍然保留 BOM

UTF-8 BOM 能免疫另一类问题（某些工具按系统 ANSI/GBK 猜测编码）。
**已实测 BOM 不影响执行**：有/无 BOM × 纯 ASCII/含中文 四种组合下，mysql 客户端全部正常。

- 自己新建或另存 `.sql` 时，请选 **UTF-8 with BOM**
- 忘了也没关系，跑一次 `python tools/ensure_sql_bom.py` 自动补齐

#### 给写脚本的人

Python 读取这些文件请用 `encoding="utf-8-sig"` 而不是 `"utf-8"`，
否则 BOM 会变成字符串里的一个字符（`\ufeff`）并混进第一条 SQL 语句。
`05_benchmark.py`、`06_query_form_comparison.py` 都已经这么处理了。

### 数据库名

`01_schema.sql` 不含 `CREATE DATABASE` 语句，请先建库。**组内统一库名 `group_project`**
（因为查询脚本第一行硬编码了 `USE group_project;`）。性能实验使用独立库 `fresh_delivery`。

### 提交用（样例数据）

```sql
CREATE DATABASE group_project DEFAULT CHARSET=utf8mb4;
USE group_project;
SOURCE sql/01_schema.sql;
SOURCE sql/02_sample_data.sql;
-- 然后运行 sql/queries_submitted.sql（48 条查询）
```

> `SOURCE` 是 mysql 命令行的指令；在 MySQL Workbench 里改成「打开文件 → 执行」即可。

### 手动跑性能实验（一步一步看过程）

⚠️ **两个前提，先读**：

1. `03_experiment_data.sql` **只插数据、不建表**，所以必须先跑 `01_schema.sql`。
2. 它和 `02_sample_data.sql` **不能同时用**。样例数据的 `store_id` 是 1–3、`product_id` 是 1–12，
   而实验数据的 `store_id` 是 1–20、`product_id` 是 1–200，一起跑会主键冲突。
   提交用样例数据，实验用放大数据，**二选一**。

```sql
-- 第 1 步：建库 + 建表（得到结构 A，14 个索引）
CREATE DATABASE fresh_delivery DEFAULT CHARSET=utf8mb4;
USE fresh_delivery;
SOURCE sql/01_schema.sql;

-- 第 2 步：生成 5 万订单 / 15 万明细（约 8 秒）
SOURCE sql/03_experiment_data.sql;
-- 脚本最后会打印自检结果：订单数、明细数、零订单顾客、零配送骑手、
-- 从未售出商品、未派单订单、已取消订单、总额不一致订单数

-- 第 3 步：测基线（结构 A）—— 不需要做任何事，01_schema.sql 建完就是 A

-- 第 4 步：加索引（结构 A → C）—— 只运行 04_indexes.sql 的第 1 段
-- 第 5 步：退回基线（C → A）——  只运行 04_indexes.sql 的第 2 段
-- 第 6 步：删外键索引（A → B）—— 只运行 04_indexes.sql 的第 3 段
-- 第 7 步：恢复基线（B → A）——  只运行 04_indexes.sql 的第 4 段
```

### `04_indexes.sql` 是 5 个独立段落，**每次只能跑一段**

| 段落名 | 作用 | 从 → 到 | 索引数 |
|---|---|---|---|
| `show_state` | **只读**：判断当前在哪个结构 | 不改动 | — |
| `apply_optimized` | 加 4 条复合/覆盖索引 | A → C | 14 → 15 |
| `revert_optimized` | 删掉那 4 条，并把外键索引加回来 | C → A | 15 → 14 |
| `drop_fk_indexes` | 删掉全部外键索引 | A → B | 14 → 9 |
| `restore_fk_indexes` | 加回外键约束（索引自动重建） | B → A | 9 → 14 |

**手工操作前先跑 `show_state`**，它会直接告诉你当前是 A / B / C 哪一个，避免跑错段落。

**不要把整个文件从头跑到尾**——那样会把"加索引"和"删索引"连着执行，状态就乱了。

#### 手工执行会遇到的三个错误码，含义分别是什么

| 错误码 | 含义 | 该怎么办 |
|---|---|---|
| `1061 Duplicate key name` | 你在**重复执行** `apply_optimized`，索引已存在 | 不是故障。你已经在结构 C，去测性能或跑 `revert_optimized` |
| `1091 Can't DROP ...; check that column/key exists` | 你在跑 `revert_optimized`，但当前**不是**结构 C | 你已经在结构 A，什么都不用做 |
| `1553 Cannot drop index ... needed in a foreign key constraint` | 漏掉了 `DROP FOREIGN KEY` 那几句 | 顺序必须是「先删外键约束 → 再删索引 → 最后加回外键」 |

**另外两个实测踩过的坑**：

- **C → A 不能直接 `DROP INDEX`**：结构 C 下外键约束已经改由新索引支撑，直接删会报
  `ERROR 1553`。正确顺序是「先删外键约束 → 再删索引 → 最后把外键加回来」。
- **每个段落末尾都有 `ANALYZE TABLE`**：不加这一步，优化器的统计信息不会更新，
  `EXPLAIN` 的行数估算会误导结论。
- **Workbench 默认开启 Safe Updates**，会拦截没有 `WHERE` 的 `UPDATE`。
  `03_experiment_data.sql` 和 `00_build_experiment_database.sql` 顶部已加
  `SET SQL_SAFE_UPDATES = 0;`，在 Workbench 里可以直接跑。

### 性能实验（一键复现，推荐）

```powershell
cd project
python results/05_benchmark.py              # 主实验：3 种结构 × 6 条查询 + 写入代价
python results/06_query_form_comparison.py  # 老师第 4 题
python results/07_acid_experiment.py        # 老师第 5 题
python results/08_make_figures.py           # 生成图表
```

`05_benchmark.py` 会自动完成：建库 → 生成实验数据 → 依次测量结构 A / C / B → 写出结果表。
每个结构都从**干净的 schema 重建**，因此三种结构之间不存在状态残留，
也不需要手动切换 `04_indexes.sql` 的段落。
其余三个脚本各自独立，`06` 会自行重建实验库。

> 被测量的查询从 `sql/queries_submitted.sql` 里按注释标题自动提取，
> 所以测的就是提交的那段 SQL，不会另写一份。要换成新版本，直接替换该文件即可。

---

## 测试环境

| 项目 | 值 |
|---|---|
| DBMS（服务器） | **MySQL Community Server 8.0.46** for Win64 on x86_64 |
| 存储引擎 | InnoDB |
| `innodb_buffer_pool_size` | 134217728 (128 MiB) |
| `innodb_flush_log_at_trx_commit` | 1 |
| 隔离级别 | REPEATABLE-READ |
| `sql_mode` | ONLY_FULL_GROUP_BY, STRICT_TRANS_TABLES, NO_ZERO_IN_DATE, NO_ZERO_DATE, ERROR_FOR_DIVISION_BY_ZERO, NO_ENGINE_SUBSTITUTION |
| 查询缓存 | 该版本已移除 `query_cache_size` 参数 |
| Windows 服务 / 端口 | `MySQL` / 127.0.0.1:3306 |
| 客户端 | Python 3 + `mysql.connector`，单连接单线程 |
| 测量协议 | 每条查询 warm-up 3 次、正式测量 7 次，报告中位数并附最小值/最大值 |

---

## 三种实验结构

| 结构 | 定义 | 索引数 |
|---|---|---:|
| **A 参考基线** | `01_schema.sql` 原样。索引全部由 `PRIMARY KEY` / `UNIQUE` / `FOREIGN KEY` 自动产生 | 14 |
| **C 优化结构** | A + 4 条有业务理由的复合/覆盖索引 | 15 |
| **B 无索引基线** | A 移除全部外键索引（先删外键约束再删索引） | 9 |

结构 C 新增的 4 条索引：

| 索引 | 列 | 目标查询 |
|---|---|---|
| `ix_oi_pid_cover` | `order_item(product_id, quantity, unit_price)` | Q1 门店销售额 |
| `ix_oi_pid_oid` | `order_item(product_id, order_id)` | Q3 买过指定商品的顾客 |
| `ix_orders_cust_amt` | `orders(customer_id, total_amount)` | Q4 每位顾客订单数与消费总额 |
| `ix_orders_rider_st` | `orders(rider_id, order_status, order_id)` | Q2 每位骑手配送量 |

---

## 主要结果（详见 `results/RESULT_TABLES.md`）

| 查询 | A 基线 | C 加索引 | B 无索引 |
|---|---:|---:|---:|
| Q1 门店销售额 | 705.2 ms | **463.6 ms（1.5× 快）** | 1037.9 ms（1.5× 慢） |
| Q2 骑手配送量 | 118.0 ms | **40.0 ms（2.9× 快）** | 562.8 ms（4.8× 慢） |
| Q3 买过指定商品的顾客（子查询） | 14.8 ms | 15.0 ms（1.02× 慢） | 45.3 ms（3.1× 慢） |
| Q3′ 同上（JOIN） | 19.3 ms | 20.6 ms（1.07× 慢） | 49.6 ms（2.5× 慢） |
| Q4 顾客订单数与消费总额 | 168.9 ms | 156.7 ms（1.1× 快） | 220.5 ms（1.3× 慢） |
| Q5 尚未派单的订单 | 33.7 ms | 33.1 ms（持平） | 37.8 ms（1.1× 慢） |

**写入与空间代价**

| 指标 | A 基线 | C 加索引 | B 无索引 |
|---|---:|---:|---:|
| 批量插入 15 万行明细（秒，中位数） | 1.414 | **1.908（+34.9%）** | 1.057（−25.2%） |
| 全库索引占用 (MB) | 8.27 | **11.78（+42%）** | 0.18 |

**结论要点**

- 索引**不是万能的**：Q1/Q2 收益显著（1.5×、2.9×），但 Q3/Q3′/Q5 反而略微变慢（1.02–1.12×）。
  原因见 `RESULT_TABLES.md`：这两条查询本身就只扫描约 3,600 行，新增索引带来的优化器选择变化
  与统计开销抵消了收益。**如实报告这一结果，比宣称"索引全面提升性能"更有说服力。**
- Q1 的收益来自**覆盖索引**：执行计划由 `Index lookup on oi using fk_item_product` 变为
  `Covering index lookup on oi using ix_oi_pid_cover`，代价估算由 125,001 降到 72,618。
- 索引的写入代价是真实存在的：净增 1 个索引带来 **+34.9%** 的批量写入耗时和 **+42%** 的索引空间。

---

## 老师 8 道理论问题：全部已写完并附实测证据

**完整成品：`report/Section9_SQL_Theory_Questions_All8.docx`**（8 题齐全，2994 词 ≈ 5.4 页）

每题都是「定义 → 本项目实测证据 → 设计影响」三段式：

| 题号 | 问题 | 本题用到的实测数据 |
|---|---|---|
| 1 | 主键 vs 外键如何保证引用完整性 | `ERROR 1452` / `1062` / `1451` 三种拒绝、孤儿记录 0 |
| 2 | 1NF/2NF/3NF 与传递依赖 | 实跑一个违反 3NF 的表，观察更新异常与删除异常 |
| 3 | INNER / LEFT / RIGHT JOIN | LEFT 200 位骑手 vs INNER 180；LEFT 5000 顾客 vs INNER 4488 |
| 4 | 子查询 vs JOIN 哪个更高效 | IN / EXISTS / JOIN+DISTINCT 三种写法 × 3 个商品 |
| 5 | ACID 与并发 | 原子性回滚、不可重复读、丢失更新 80 vs 70 |
| 6 | 索引原理与代价 | 覆盖索引生效前后、写入 +34.9%、空间 +42% |
| 7 | GROUP BY / HAVING vs WHERE | 50000→47569 行、4485→4227 组、`ERROR 1111` |
| 8 | VIEW vs STORED PROCEDURE | 实建 `v_store_revenue` 与 `sp_create_order` 并调用 |

> 第 1/2/3/7/8 题的实测输出保存在 `results/Q1_Q2_Q3_Q7_Q8_demo_output.txt`。
> ⚠️ **页数提醒**：8 题全文约 5.4 页，装进 10–12 页正文会挤掉其它章节。
> 建议正文只放精简版（每題 2–3 句），全文放附录 —— 但要先向老师确认附录是否计页数。

### 第 4 题结论（三种写法 × 3 个不同选择性的商品 × 各 7 次测量）

以结构 A（参考基线）为例，商品 `product_id = 5`（买家 2,182 人）：

| 写法 | 中位数 | 相对 IN 子查询 |
|---|---:|---|
| V1 `IN (SELECT ...)` | 14.73 ms | 基准 |
| V2 `JOIN` + `DISTINCT` | 19.81 ms | **慢 34.5%（最慢）** |
| V3 `EXISTS` 半连接 | 14.39 ms | 快 2.3%（噪声内） |

三个商品（2,182 / 502 / 340 个买家）合起来看：

- **`JOIN + DISTINCT` 一致地最慢**，比 `IN` 慢 **2.1% – 34.5%**
- **`EXISTS` 与 `IN` 打平**：相对差异在 **−8.9% ~ +4.2%** 之间，且**方向不一致**
  （两个商品上 EXISTS 略快、一个略慢），说明没有稳定的优势

补充说明：

- 三种写法在每组测试中返回**完全相同的结果集**（脚本逐组断言），对比才有意义。
- `JOIN + DISTINCT` 最慢的原因：`DISTINCT` 需要额外的去重排序；`IN` 被优化器改写成
  **半连接（semi-join）**，执行计划里是 `Materialize with deduplication` + 每值一次索引查找。
- **本组数据不支持老师 Answer Key 中「`EXISTS` 常优于 `IN`」的说法**——在这里两者打平。
  可能原因：优化器已把 `IN` 改写为半连接，因此**写法的影响小于索引的影响**：
  同一条 `IN` 查询在有外键索引时 14.8 ms、移除索引后 45.3 ms（**3.1×**），
  而改写法只带来 1.3× 的变化。

### 第 5 题结论（实测数字）

| 测试 | 结果 |
|---|---|
| 原子性 | 事务中途违反 `CHECK(quantity>0)` 后 `ROLLBACK`，订单头与已写入的明细**全部撤销**（0 / 0） |
| 隔离性（不可重复读） | 另一会话提交 88.88 后，本事务两次读到的值完全相同（218662.50） |
| 丢失更新（无锁读-改-写） | 两个事务都读到 100，最终 **80**，正确应为 **70** → **丢失一次扣减**（业务上即超卖） |
| 丢失更新（`SELECT ... FOR UPDATE`） | 第二个事务被阻塞 **1.00 秒**，读到新值 90，最终 **70** ✅ |
| 一致性不变量 | 孤儿明细 0 条、总额不一致 0 条；但 `orders.store_id` 与明细商品门店不符**无法被数据库拒绝** |

---

## 三个必须写进报告的实现细节

本组实际使用 MySQL **8.0.46**。以下三点影响了脚本写法，均已实测确认：

1. **数据生成不用 `RAND()`，改用 `SHA2(..., 256)`。**
   这样同一脚本在任何机器上重复执行都会得到完全相同的数据集，实验可复现。
2. **`EXPLAIN` 默认输出树形计划**。需要传统表格时必须显式写
   `EXPLAIN FORMAT=TRADITIONAL`。树形计划反而更直观（会直接写出 `Covering index lookup on ... using ...`），
   本项目两种格式都采集。
3. **MySQL 会自动删除被新索引取代的外键自动索引**。在结构 A 上创建 4 条复合索引后，
   索引总数由 14 变为 **15**（而非 14+4=18）：`order_item.fk_item_product`、
   `orders.fk_order_customer`、`orders.fk_order_rider` 三条单列外键索引被复合索引取代并删除，
   外键**约束**仍然有效。净效果是「新增 4 条复合索引、移除 3 条单列索引，净增 1 个」。
   这也导致回退时不能直接 `DROP INDEX`（报 `ERROR 1553`），必须先删外键约束、再删索引、最后加回外键。

---

## 数据说明与局限

- **实验数据为合成数据。** 本组无法取得真实社区生鲜平台的运营数据，因此用
  `03_experiment_data.sql` 生成。伪随机来自 `SHA2()` 哈希而非 `RAND()`，
  同一脚本在任何机器上重复执行都会得到完全相同的数据集，实验可复现。
- **提交给老师的样例数据仍是 12 个订单**（`02_sample_data.sql`），未被实验数据影响。
- 刻意建模的真实性特征：门店订单量头部效应、顾客复购集中度、500 位零订单顾客、
  20 位零配送骑手、20 个从未售出的商品、约 15% 未派单订单、订单状态与订单新旧相关。
- **局限**：未建模星期效应、节假日、促销与季节性；实验为本机单用户单连接，
  规模 5 万订单，未测试真并发热点，结论不可外推到生产级数据量。
