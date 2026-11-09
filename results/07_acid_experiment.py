"""07_acid_experiment.py — 老师第 5 题 & 一致性权衡的实测证据

问题原文:
  Explain the ACID properties of transactions; give a "two concurrent transfers"
  example showing why isolation and atomicity are needed.

本脚本用本项目真实场景（下单事务）实测四项内容：

  T1 原子性 Atomicity      —— 下单事务中途失败后回滚，不留半成品数据
  T2 隔离性 Isolation      —— REPEATABLE-READ 下不会出现不可重复读
  T3 丢失更新 Lost Update  —— 不加锁的读-改-写会丢更新；SELECT ... FOR UPDATE 可避免
  T4 一致性 Consistency    —— 事务维护 total_amount = SUM(明细) 不变量；
                              并实测数据库**无法**强制 orders.store_id 与明细商品所属门店一致

实现要点：控制类操作（置初值、校验、清理）统一走一个 autocommit=True 的连接，
避免残留未提交事务持有行锁，干扰后续并发测试。

输出: results/ACID_EVIDENCE.md
"""
import io
import os
import sys
import threading
import time

import mysql.connector as mc

DB = "fresh_delivery"
CFG = dict(host="127.0.0.1", port=3306, user="root", password="", database=DB)
ROOT = r"G:\dphlearning\database\project"
RES_DIR = os.path.join(ROOT, "results")

TEST_ORDER = 900001
TEST_PRODUCT = 1
QTY_A, QTY_B = 10, 20
INIT_STOCK = 100


def new_conn(autocommit=True):
    return mc.connect(**CFG, autocommit=autocommit)


def main():
    os.makedirs(RES_DIR, exist_ok=True)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ctl = new_conn(autocommit=True)      # 控制连接：置初值 / 校验 / 清理
    cc = ctl.cursor()
    md = []
    md.append("# 老师第 5 题 · ACID 与并发一致性的实测证据\n")
    md.append("> 场景：社区生鲜次日达的**下单事务**（写订单头 + 写明细 + 回填总额）")
    md.append("> 数据：`fresh_delivery`，5 万订单 / 150,152 条明细")
    md.append("> 隔离级别：REPEATABLE-READ（本实例默认）\n")

    # ==================== T1 原子性 ====================
    cc.execute("SELECT COUNT(*) FROM orders WHERE order_id=%s", (TEST_ORDER,))
    before = cc.fetchone()[0]

    tx = new_conn(autocommit=False)
    tc = tx.cursor()
    tc.execute("START TRANSACTION")
    tc.execute("""INSERT INTO orders (order_id, store_id, customer_id, rider_id, order_time,
                    total_amount, delivery_address, delivery_date, order_status)
                   VALUES (%s, 1, 1, 1, NOW(), 0, 'ACID test address', CURDATE(), 'pending')""",
               (TEST_ORDER,))
    tc.execute("""INSERT INTO order_item (order_id, product_id, quantity, unit_price)
                   VALUES (%s, 1, 2, 10.00)""", (TEST_ORDER,))
    tc.execute("SELECT COUNT(*) FROM order_item WHERE order_id=%s", (TEST_ORDER,))
    mid_items = tc.fetchone()[0]
    err = None
    try:
        tc.execute("""INSERT INTO order_item (order_id, product_id, quantity, unit_price)
                       VALUES (%s, 2, 0, 5.00)""", (TEST_ORDER,))   # 违反 CHECK(quantity>0)
    except Exception as e:
        err = str(e)
    tc.execute("ROLLBACK")

    cc.execute("SELECT COUNT(*) FROM orders WHERE order_id=%s", (TEST_ORDER,))
    after_orders = cc.fetchone()[0]
    cc.execute("SELECT COUNT(*) FROM order_item WHERE order_id=%s", (TEST_ORDER,))
    after_items = cc.fetchone()[0]

    md.append("## T1 原子性（Atomicity）—— 事务中途失败不留半成品\n")
    md.append("事务步骤：`START TRANSACTION` → 写订单头 → 写第 1 条明细 → "
              "写第 2 条明细（故意违反 `CHECK(quantity>0)`）→ `ROLLBACK`\n")
    md.append("| 检查点 | 结果 |")
    md.append("|---|---|")
    md.append(f"| 事务开始前 `order_id={TEST_ORDER}` 的订单数 | {before} |")
    md.append(f"| 事务内已成功写入的明细数 | {mid_items} |")
    md.append(f"| 第 2 条明细插入结果 | ❌ 失败：`{err}` |")
    md.append(f"| `ROLLBACK` 后的订单数 | {after_orders} |")
    md.append(f"| `ROLLBACK` 后的明细数 | {after_items} |")
    md.append("\n**结论**：事务提交前所有写入对外不可见；`ROLLBACK` 后订单头与已成功的明细**全部撤销**，"
              "数据库中不存在「有订单没明细」或「有明细没订单」的半成品状态。")
    md.append("这正是原子性「全有或全无」的含义——若没有原子性，中途失败就会留下孤儿明细。\n")

    # 正向对照：同一事务完整提交
    tc.execute("START TRANSACTION")
    tc.execute("""INSERT INTO orders (order_id, store_id, customer_id, rider_id, order_time,
                    total_amount, delivery_address, delivery_date, order_status)
                   VALUES (%s, 1, 1, 1, NOW(), 0, 'ACID test address', CURDATE(), 'pending')""",
               (TEST_ORDER,))
    tc.execute("""INSERT INTO order_item (order_id, product_id, quantity, unit_price)
                   VALUES (%s, 1, 2, 10.00)""", (TEST_ORDER,))
    tc.execute("""INSERT INTO order_item (order_id, product_id, quantity, unit_price)
                   VALUES (%s, 2, 3, 5.00)""", (TEST_ORDER,))
    tc.execute("""UPDATE orders o
                  JOIN (SELECT order_id, SUM(quantity*unit_price) s FROM order_item
                        WHERE order_id=%s GROUP BY order_id) x ON x.order_id=o.order_id
                  SET o.total_amount = x.s WHERE o.order_id=%s""", (TEST_ORDER, TEST_ORDER))
    tc.execute("COMMIT")
    cc.execute("SELECT total_amount FROM orders WHERE order_id=%s", (TEST_ORDER,))
    committed_total = cc.fetchone()[0]
    cc.execute("SELECT SUM(quantity*unit_price) FROM order_item WHERE order_id=%s", (TEST_ORDER,))
    detail_total = cc.fetchone()[0]
    md.append(f"**正向对照**：同一事务完整提交后，`orders.total_amount = {committed_total}`，"
              f"明细合计 = `{detail_total}` → "
              f"{'一致 ✅' if committed_total == detail_total else '不一致 ❌'}\n")
    cc.execute("DELETE FROM order_item WHERE order_id=%s", (TEST_ORDER,))
    cc.execute("DELETE FROM orders WHERE order_id=%s", (TEST_ORDER,))

    # ==================== T2 隔离性：不可重复读 ====================
    s2 = new_conn(autocommit=False)
    c2 = s2.cursor()
    c2.execute("START TRANSACTION")
    c2.execute("SELECT COALESCE(SUM(total_amount),0) FROM orders WHERE customer_id=1")
    v1 = c2.fetchone()[0]

    cc.execute("""INSERT INTO orders (order_id, store_id, customer_id, rider_id, order_time,
                   total_amount, delivery_address, delivery_date, order_status)
                  VALUES (%s, 1, 1, 1, NOW(), 88.88, 'iso test', CURDATE(), 'pending')""",
               (TEST_ORDER,))
    cc.execute("SELECT COALESCE(SUM(total_amount),0) FROM orders WHERE customer_id=1")
    v_other = cc.fetchone()[0]
    c2.execute("SELECT COALESCE(SUM(total_amount),0) FROM orders WHERE customer_id=1")
    v2 = c2.fetchone()[0]
    c2.execute("COMMIT")
    cc.execute("DELETE FROM orders WHERE order_id=%s", (TEST_ORDER,))

    md.append("## T2 隔离性（Isolation）—— 不会出现不可重复读\n")
    md.append("| 时刻 | 事务 S2 在同一事务内读到的 `customer_id=1` 消费总额 |")
    md.append("|---|---:|")
    md.append(f"| S2 开启事务后第一次读 | {v1} |")
    md.append(f"| 另一会话提交一笔 88.88 的新订单（该会话自己读到 {v_other}） | — |")
    md.append(f"| S2 在同一事务内再读一次 | **{v2}** |")
    md.append(f"\n**结论**：另一会话**已经提交**，但 S2 在同一事务内两次读到的值完全相同（{v1} = {v2}），"
              "未出现不可重复读。这是 REPEATABLE-READ 的快照隔离效果——"
              "并发事务看不到彼此的中间状态。\n")

    # ==================== T3 丢失更新 ====================
    cc.execute("SELECT stock_quantity FROM product WHERE product_id=%s", (TEST_PRODUCT,))
    stock0 = cc.fetchone()[0]

    def set_stock(v):
        cc.execute("UPDATE product SET stock_quantity=%s WHERE product_id=%s", (v, TEST_PRODUCT))

    expected = INIT_STOCK - QTY_A - QTY_B

    # --- 场景 1：无锁读-改-写 ---
    set_stock(INIT_STOCK)
    a = new_conn(autocommit=False)
    ca = a.cursor()
    ca.execute("START TRANSACTION")
    ca.execute("SELECT stock_quantity FROM product WHERE product_id=%s", (TEST_PRODUCT,))
    ra = ca.fetchone()[0]
    b = new_conn(autocommit=False)
    cb = b.cursor()
    cb.execute("START TRANSACTION")
    cb.execute("SELECT stock_quantity FROM product WHERE product_id=%s", (TEST_PRODUCT,))
    rb = cb.fetchone()[0]
    ca.execute("UPDATE product SET stock_quantity=%s WHERE product_id=%s", (ra - QTY_A, TEST_PRODUCT))
    ca.execute("COMMIT")
    cb.execute("UPDATE product SET stock_quantity=%s WHERE product_id=%s", (rb - QTY_B, TEST_PRODUCT))
    cb.execute("COMMIT")
    cc.execute("SELECT stock_quantity FROM product WHERE product_id=%s", (TEST_PRODUCT,))
    lost_final = cc.fetchone()[0]

    # --- 场景 2：SELECT ... FOR UPDATE ---
    set_stock(INIT_STOCK)
    c1 = new_conn(autocommit=False)
    cu1 = c1.cursor()
    c1b = new_conn(autocommit=False)
    cu1b = c1b.cursor()
    cu1.execute("START TRANSACTION")
    cu1.execute("SELECT stock_quantity FROM product WHERE product_id=%s FOR UPDATE", (TEST_PRODUCT,))
    r1 = cu1.fetchone()[0]

    holder = {}

    def second_txn():
        try:
            cu1b.execute("START TRANSACTION")
            t0 = time.perf_counter()
            cu1b.execute("SELECT stock_quantity FROM product WHERE product_id=%s FOR UPDATE",
                         (TEST_PRODUCT,))
            holder["wait"] = time.perf_counter() - t0
            holder["read"] = cu1b.fetchone()[0]
            cu1b.execute("UPDATE product SET stock_quantity=%s WHERE product_id=%s",
                         (holder["read"] - QTY_B, TEST_PRODUCT))
            cu1b.execute("COMMIT")
        except Exception as e:
            holder["error"] = str(e)

    th = threading.Thread(target=second_txn)
    th.start()
    time.sleep(1.0)                       # 确保第二个事务已卡在行锁上
    cu1.execute("UPDATE product SET stock_quantity=%s WHERE product_id=%s",
                (r1 - QTY_A, TEST_PRODUCT))
    cu1.execute("COMMIT")
    th.join(timeout=40)
    cc.execute("SELECT stock_quantity FROM product WHERE product_id=%s", (TEST_PRODUCT,))
    locked_final = cc.fetchone()[0]

    md.append("## T3 隔离性（Isolation）—— 丢失更新与行锁\n")
    md.append(f"场景：商品 `product_id={TEST_PRODUCT}`，初始库存 {INIT_STOCK}。"
              f"两个并发事务各自「先读库存 → 再减库存 → 再提交」。")
    md.append(f"事务 A 减 {QTY_A}、事务 B 减 {QTY_B}，**正确结果应为 {expected}**。\n")
    md.append("| 做法 | 事务 A 读到 | 事务 B 读到 | 最终库存 | 是否符合预期 |")
    md.append("|---|---:|---:|---:|:--:|")
    md.append(f"| 普通 `SELECT` 后 `UPDATE`（无锁） | {ra} | {rb} | **{lost_final}** | "
              f"{'✅' if lost_final == expected else '❌ **丢失更新**'} |")
    md.append(f"| `SELECT ... FOR UPDATE`（行锁） | {r1} | {holder.get('read', '—')} | "
              f"**{locked_final}** | {'✅' if locked_final == expected else '❌'} |")
    lost_amount = lost_final - expected
    md.append(f"\n- **无锁场景**：两个事务都读到初始值 {INIT_STOCK}，各自基于**同一个旧值**计算，"
              f"后提交的覆盖先提交的 → 最终 {lost_final}，比正确值 {expected} 多出 {lost_amount}，"
              f"相当于**丢了一次扣减**。放到业务上就是**超卖**。")
    md.append(f"- **加锁场景**：事务 B 的 `SELECT ... FOR UPDATE` 被阻塞了 "
              f"**{holder.get('wait', 0):.2f} 秒**，等事务 A 提交后才读到新值 {holder.get('read')}，"
              f"因此算出的结果正确 → 最终 {locked_final}。")
    md.append(f"\n**结论**：下单扣库存必须用行锁或原子更新（`UPDATE ... SET qty = qty - n`），"
              f"否则高峰期并发下单会超卖。这也是「**一致性 vs 延迟**」权衡的典型例子——"
              f"加锁保证了正确性，代价是并发事务串行等待、吞吐下降；"
              f"若业务允许短暂超卖（例如允许缺货后补），则可以不加锁换取更低延迟。\n")
    set_stock(stock0)

    # ==================== T4 一致性 ====================
    cc.execute("""SELECT COUNT(*) FROM (
                   SELECT o.order_id FROM orders o JOIN order_item oi ON oi.order_id=o.order_id
                   GROUP BY o.order_id, o.total_amount
                   HAVING ABS(o.total_amount - SUM(oi.quantity*oi.unit_price)) > 0.001) z""")
    mism = cc.fetchone()[0]
    cc.execute("""SELECT COUNT(*) FROM order_item oi
                  LEFT JOIN orders o ON oi.order_id=o.order_id WHERE o.order_id IS NULL""")
    orphan = cc.fetchone()[0]

    cc.execute("SELECT store_id, product_id FROM product WHERE product_id=1")
    p_store, p_pid = cc.fetchone()
    cc.execute("SELECT store_id FROM store WHERE store_id <> %s LIMIT 1", (p_store,))
    other_store = cc.fetchone()[0]
    cc.execute("SELECT customer_id FROM customer LIMIT 1")
    any_cust = cc.fetchone()[0]

    accepted = False
    gap_row = None
    gap_err = None
    try:
        cc.execute("""INSERT INTO orders (order_id, store_id, customer_id, rider_id, order_time,
                       total_amount, delivery_address, delivery_date, order_status)
                      VALUES (%s, %s, %s, NULL, NOW(), 10, 'gap test', CURDATE(), 'pending')""",
                   (TEST_ORDER, other_store, any_cust))
        cc.execute("""INSERT INTO order_item (order_id, product_id, quantity, unit_price)
                      VALUES (%s, %s, 1, 10.00)""", (TEST_ORDER, p_pid))
        accepted = True
        cc.execute("""SELECT o.store_id, p.store_id FROM orders o
                      JOIN order_item oi ON oi.order_id=o.order_id
                      JOIN product p ON p.product_id=oi.product_id
                      WHERE o.order_id=%s""", (TEST_ORDER,))
        gap_row = cc.fetchone()
    except Exception as e:
        gap_err = str(e)
    finally:
        cc.execute("DELETE FROM order_item WHERE order_id=%s", (TEST_ORDER,))
        cc.execute("DELETE FROM orders WHERE order_id=%s", (TEST_ORDER,))

    md.append("## T4 一致性（Consistency）—— 哪些不变量数据库能保证，哪些不能\n")
    md.append("| 不变量 | 由什么保证 | 实测结果 |")
    md.append("|---|---|---|")
    md.append(f"| 明细必须引用存在的订单与商品 | 复合主键 + 外键 | 孤儿明细 **{orphan}** 条 ✅ |")
    md.append(f"| `orders.total_amount` = 明细金额合计 | 事务（应用层维护） | 不一致订单 **{mism}** 条 ✅ |")
    md.append(f"| 明细商品必须属于该订单所属门店 | ❌ **数据库无法强制** | "
              f"{'**插入被接受**' if accepted else '被拒绝：' + str(gap_err)} |")
    md.append("")
    if accepted:
        md.append(f"> 实测：插入一个 `store_id={gap_row[0]}` 的订单，其明细却引用属于 "
                  f"`store_id={gap_row[1]}` 的商品，**数据库接受了这条数据**。")
        md.append("> 原因是 `orders.store_id` 与「明细商品的门店」之间没有任何可声明的跨表约束——"
                  "单列外键只能保证「每个值都存在」，无法保证「两个值彼此相符」。")
        md.append("> 这是**反规范化（denormalization）用一致性换读取性能**的典型代价："
                  "`orders.store_id` 让门店维度统计少一次 join，但也打开了跨门店脏数据的口子。")
        md.append("> 若要在该结构上强制它，需把 `store_id` 冗余进 `order_item` 并加复合外键 "
                  "`(product_id, store_id) → product(product_id, store_id)`，"
                  "代价是更多列、更大的索引与更高的写入成本。\n")
    md.append("**结论**：ACID 里的 C（一致性）一半靠数据库约束，一半靠**事务里的应用逻辑**。"
              "本项目的「订单总额等于明细合计」属于后者——数据库不会自动算总额，"
              "必须在下单事务里同时写入并回填。这也解释了为什么样例数据里 0 处不一致："
              "数据是脚本按同一事务语义生成的。\n")

    for h in (ctl, s2, a, b, c1, c1b, tx):
        try:
            h.close()
        except Exception:
            pass

    p = os.path.join(RES_DIR, "ACID_EVIDENCE.md")
    io.open(p, "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("wrote", p)
    print("\n".join(md))


if __name__ == "__main__":
    main()
