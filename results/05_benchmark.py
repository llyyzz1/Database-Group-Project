"""05_benchmark.py — Topic 2 社区生鲜次日达 索引实验基准测试

测量三种结构下的核心查询表现：
    A 参考基线   = 01_schema.sql 原样
    C 优化结构   = A + 4 条复合/覆盖索引
    B 无索引基线 = A 移除全部外键索引

被测量的查询直接从成员 4 提交的 Select_Part_LUO Yipeng(4).sql 中按注释标题提取，
保证"测的就是提交的那段 SQL"，不另行改写。

输出:
    results/<structure>/raw_<structure>.json   原始数据（每次测量都留痕）
    results/RESULT_TABLES.md                   4 张可直接放进报告的结果表
"""
import io
import json
import os
import statistics
import sys
import time

import mysql.connector as mc

# ---------------- 配置 ----------------
DB = "fresh_delivery"          # 独立实验库，不碰组里其他库
CFG = dict(host="127.0.0.1", port=3306, user="root", password="", database=DB)

ROOT = r"G:\dphlearning\database\project"
SQL_DIR = os.path.join(ROOT, "sql")
RES_DIR = os.path.join(ROOT, "results")

_QUERY_CANDIDATES = [
    os.path.join(SQL_DIR, "queries_submitted.sql"),   # 项目内副本（首选，保证项目自包含）
    (r"C:\Users\LENOVO\AppData\Roaming\dsh-desktop\harness\attachments\v1\files"
     r"\c4\c421eb9a610c6624d72205b85d9aa8a6f7472d0cd66203eeb40c9836be71d571"
     r"\Select_Part_LUO Yipeng(4).sql"),               # 原始附件路径（备用）
]
QUERY_FILE = next((p for p in _QUERY_CANDIDATES if os.path.exists(p)), _QUERY_CANDIDATES[0])

WARMUP, RUNS = 3, 7
WRITE_BATCH = 150000

# 从提交文件中提取的查询（按注释标题匹配）
WORKLOAD = [
    ("Q1 门店销售额（经 order_item 汇总）", "Calculate the sales of the store based on the order details"),
    ("Q2 每位骑手配送量（含零单骑手）",      "Query all riders and the quantity of delivery orders"),
    ("Q3 买过指定商品的顾客（子查询版）",    "Query customers who have purchased a specific product"),
    ("Q3' 买过指定商品的顾客（JOIN 版）",    "Query the customers who have purchased a certain product"),
    ("Q4 每位顾客订单数与消费总额",          "Query the number of orders and the total consumption amount of the customer"),
    ("Q5 尚未派单的订单",                    "Orders that have not assigned a rider yet"),
]

STRUCTURES = [
    ("A_reference_baseline", "结构 A · 参考基线（原样）", []),
    ("C_optimized",          "结构 C · 加 4 条业务索引", ["apply_optimized"]),
    ("B_no_index",           "结构 B · 移除全部外键索引", ["drop_fk_indexes"]),
]


# ---------------- 工具函数 ----------------
def read(path):
    # utf-8-sig：SQL 文件带 UTF-8 BOM（为了让 Workbench 正确识别中文注释），
    # 用 utf-8-sig 读取会把 BOM 剥掉，否则它会混进第一条语句里。
    return io.open(path, encoding="utf-8-sig").read()


def split_sql(text):
    """去掉 -- 注释后按分号切分（忽略字符串/反引号内的分号）。"""
    out, buf, i, n = [], [], 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "-" and text[i:i + 2] == "--":
            j = text.find("\n", i)
            i = n if j == -1 else j + 1
            continue
        if ch in ("'", '"', "`"):
            q = ch
            buf.append(ch)
            i += 1
            while i < n:
                buf.append(text[i])
                if text[i] == q and text[i - 1] != "\\":
                    i += 1
                    break
                i += 1
            continue
        if ch == ";":
            if "".join(buf).strip():
                out.append("".join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    if "".join(buf).strip():
        out.append("".join(buf).strip())
    return out


def sections(path):
    """按 `-- ### SECTION: name` 把 SQL 文件切成段落。"""
    text = read(path)
    parts, cur, name = {}, [], None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("-- ### SECTION:"):
            if name:
                parts[name] = "\n".join(cur)
            # 标记形如 "-- ### SECTION: apply_optimized -> A 变 C"，只取箭头前的段落名
            name = s.split(":", 1)[1].split("->")[0].strip()
            cur = []
            continue
        if name is not None and s.startswith("-- ### SECTION"):
            continue
        if name is not None:
            cur.append(line)
    if name:
        parts[name] = "\n".join(cur)
    return parts


def query_blocks(path):
    """按 `-- 注释` 抽出 (标题, SQL) 对。"""
    out, label, buf = [], None, []
    for line in read(path).splitlines():
        s = line.strip()
        if s.startswith("--"):
            if "".join(buf).strip():
                out.append((label, "".join(buf).strip()))
                buf = []
            label = s.lstrip("-").strip()
            continue
        buf.append(line + "\n")
    if "".join(buf).strip():
        out.append((label, "".join(buf).strip()))
    return out


def run_sql(conn, text, timing=False):
    cur = conn.cursor()
    t0 = time.perf_counter()
    for stmt in split_sql(text):
        cur.execute(stmt)
        # 必须把结果集取空，否则下一个 execute 会报 "Unread result found"
        try:
            cur.fetchall()
        except Exception:
            pass
        try:
            while cur.nextset():
                cur.fetchall()
        except Exception:
            pass
    dt = time.perf_counter() - t0
    return dt


def measure(conn, sql, warmup=WARMUP, runs=RUNS):
    cur = conn.cursor()
    for _ in range(warmup):
        cur.execute(sql)
        cur.fetchall()
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        cur.execute(sql)
        cur.fetchall()
        times.append((time.perf_counter() - t0) * 1000)
    # `EXPLAIN` 默认输出**树形计划**，
    # 传统表格须显式写成 EXPLAIN FORMAT=TRADITIONAL。两种都采集：
    #   plan —— 结构化字段，用于结果表的"访问类型/索引/扫描行数"列
    #   tree —— 树形文本，作为报告里最直观的执行计划证据
    cur.execute("EXPLAIN FORMAT=TRADITIONAL " + sql)
    cols = list(cur.column_names)
    plan = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.execute("EXPLAIN " + sql)
    tree = "\n".join(str(r[0]) for r in cur.fetchall())
    cur.execute(sql)
    nrows = len(cur.fetchall())
    return {
        "median_ms": round(statistics.median(times), 3),
        "min_ms": round(min(times), 3),
        "max_ms": round(max(times), 3),
        "all_ms": [round(t, 3) for t in times],
        "rows_returned": nrows,
        "tree_plan": tree,
        "explain": [{"table": p.get("table"), "type": p.get("type"),
                     "key": p.get("key"), "rows": p.get("rows"),
                     "Extra": p.get("Extra")} for p in plan],
    }


def index_inventory(conn):
    cur = conn.cursor()
    cur.execute("""SELECT table_name, index_name,
                          GROUP_CONCAT(column_name ORDER BY seq_in_index) AS cols
                   FROM information_schema.STATISTICS
                   WHERE table_schema = %s
                   GROUP BY table_name, index_name
                   ORDER BY table_name, index_name""", (DB,))
    return [{"table": t, "index": i, "cols": c} for t, i, c in cur.fetchall()]


def table_sizes(conn):
    cur = conn.cursor()
    cur.execute("""SELECT table_name,
                          ROUND((data_length)/1024/1024, 2)          AS data_mb,
                          ROUND((index_length)/1024/1024, 2)         AS index_mb,
                          ROUND((data_length+index_length)/1024/1024,2) AS total_mb
                   FROM information_schema.TABLES
                   WHERE table_schema = %s AND table_type='BASE TABLE'
                   ORDER BY table_name""", (DB,))
    return [{"table": t, "data_mb": float(d), "index_mb": float(i), "total_mb": float(m)}
            for t, d, i, m in cur.fetchall()]


def row_counts(conn):
    cur = conn.cursor()
    out = {}
    for t in ["store", "product", "customer", "rider", "orders", "order_item"]:
        cur.execute(f"SELECT COUNT(*) FROM `{t}`")
        out[t] = cur.fetchone()[0]
    return out


def write_cost(conn, batch=WRITE_BATCH):
    """在结构与 order_item 相同的空表上批量插入，隔离索引维护成本。"""
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS _write_probe")
    cur.execute("CREATE TABLE _write_probe LIKE order_item")
    times = []
    for _ in range(3):
        cur.execute("TRUNCATE TABLE _write_probe")
        t0 = time.perf_counter()
        cur.execute(f"""INSERT INTO _write_probe (order_id, product_id, quantity, unit_price)
                        SELECT order_id, product_id, quantity, unit_price
                        FROM order_item LIMIT {batch}""")
        times.append(time.perf_counter() - t0)
    cur.execute("ANALYZE TABLE _write_probe")
    cur.fetchall()
    cur.execute("""SELECT COUNT(DISTINCT index_name)
                   FROM information_schema.STATISTICS
                   WHERE table_schema=%s AND table_name='_write_probe'""", (DB,))
    n_idx = cur.fetchone()[0]
    cur.execute("""SELECT ROUND(index_length/1024/1024, 2)
                   FROM information_schema.TABLES
                   WHERE table_schema=%s AND table_name='_write_probe'""", (DB,))
    row = cur.fetchone()
    idx_mb = float(row[0]) if row and row[0] is not None else 0.0
    cur.execute("DROP TABLE _write_probe")
    return {"median_s": round(statistics.median(times), 3),
            "all_s": [round(t, 3) for t in times],
            "rows": batch, "indexes": n_idx, "index_mb": float(idx_mb or 0)}


# ---------------- 主流程 ----------------
def main():
    os.makedirs(RES_DIR, exist_ok=True)
    log = []

    def say(msg):
        log.append(msg)
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(msg, flush=True)

    # 建库
    root = mc.connect(host=CFG["host"], port=CFG["port"], user=CFG["user"], password=CFG["password"])
    rc = root.cursor()
    schema_sql = read(os.path.join(SQL_DIR, "01_schema.sql"))
    data_sql = read(os.path.join(SQL_DIR, "03_experiment_data.sql"))

    def rebuild():
        """每个结构都从干净 schema 重建数据库，杜绝结构之间的状态残留。

        这一点不是洁癖：实测发现 MySQL 会在新索引能替代外键自动索引时自动删除
        原外键索引，导致结构之间无法简单地"加了再删回去"。每次重建最可靠。
        """
        rc.execute(f"DROP DATABASE IF EXISTS {DB}")
        rc.execute(f"CREATE DATABASE {DB} DEFAULT CHARSET=utf8mb4")
        c = mc.connect(**CFG)
        c.autocommit = True
        run_sql(c, schema_sql)
        t = run_sql(c, data_sql)
        return c, t

    say("=== 1) 建表 + 生成实验数据 ===")
    conn, t = rebuild()
    say(f"01_schema.sql + 03_experiment_data.sql 执行完成，用时 {t:.2f}s")
    counts = row_counts(conn)
    say("行数: " + ", ".join(f"{k}={v}" for k, v in counts.items()))

    # 提取提交文件中的查询
    blocks = query_blocks(QUERY_FILE)
    workload = []
    for name, label in WORKLOAD:
        hit = None
        for lab, body in blocks:
            if lab and label.lower() in lab.lower():
                hit = body.rstrip().rstrip(";")
                break
        if hit is None:
            say(f"[警告] 未在提交文件中找到查询: {label}")
            continue
        workload.append((name, hit))
    say(f"\n=== 3) 工作负载：从提交文件中提取到 {len(workload)} 条查询 ===")
    for n, _ in workload:
        say(f"    - {n}")

    sec = sections(os.path.join(SQL_DIR, "04_indexes.sql"))
    results, inventories, sizes, writes = {}, {}, {}, {}

    for idx_struct, (key, title, apply_sections) in enumerate(STRUCTURES):
        say(f"\n=== 4.{idx_struct+1}) 测量 {title} ===")
        if idx_struct > 0:
            conn.close()
            conn, t = rebuild()
            say(f"    已从干净 schema 重建数据库（含数据生成 {t:.2f}s）")
        for s in apply_sections:
            run_sql(conn, sec[s])
            say(f"    已应用 04_indexes.sql 段落: {s}")
        run_sql(conn, "ANALYZE TABLE store, product, customer, rider, orders, order_item", timing=False)
        time.sleep(0.5)

        inventories[key] = index_inventory(conn)
        sizes[key] = table_sizes(conn)
        say(f"    索引数: {len(inventories[key])}")

        results[key] = {}
        for name, sql in workload:
            m = measure(conn, sql)
            results[key][name] = m
            say(f"    {name:<38} 中位数 {m['median_ms']:>9.3f} ms  (最快 {m['min_ms']:.3f}, 最慢 {m['max_ms']:.3f}, 返回 {m['rows_returned']} 行)")

        w = write_cost(conn)
        writes[key] = w
        say(f"    写入代价: 批量插入 {w['rows']} 行耗时中位数 {w['median_s']}s（{w['indexes']} 个索引，占 {w['index_mb']} MB）")

        # 收集原始数据后清理结构
        os.makedirs(os.path.join(RES_DIR, key), exist_ok=True)
        json.dump({"structure": title, "queries": results[key], "indexes": inventories[key],
                   "table_sizes": sizes[key], "write_cost": w, "row_counts": counts},
                  io.open(os.path.join(RES_DIR, key, f"raw_{key}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)

    # 收尾：把数据库留在结构 A（参考基线）状态，便于交付与复核
    conn.close()
    conn, _ = rebuild()
    run_sql(conn, "ANALYZE TABLE store, product, customer, rider, orders, order_item")
    say("\n已重建为结构 A（参考基线），数据库留在可交付状态")

    # ---------------- 结果表 ----------------
    env = [
        ("DBMS（服务器）", "MySQL Community Server 8.0.46 for Win64 on x86_64"),
        ("存储引擎", "InnoDB"),
        ("innodb_buffer_pool_size", "134217728 (128 MiB)"),
        ("innodb_flush_log_at_trx_commit", "1"),
        ("隔离级别", "REPEATABLE-READ"),
        ("Windows 服务名 / 端口", "MySQL / 127.0.0.1:3306"),
        ("客户端", "Python mysql.connector，单连接单线程"),
        ("测量协议", f"每条查询 warm-up {WARMUP} 次，正式测量 {RUNS} 次，报告中位",
                     ),
    ]

    md = []
    md.append("# Topic 2 社区生鲜次日达 · 性能实验结果表\n")
    md.append(f"> 生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"> 被测量查询取自 `Select_Part_LUO Yipeng(4).sql`（提交版）\n")

    md.append("## 表 A 测试环境\n")
    md.append("| 项目 | 值 |")
    md.append("|---|---|")
    for k, v in env:
        md.append(f"| {k} | {v} |")

    md.append("\n## 表 B 数据集规模\n")
    md.append("| 表 | 行数 | 说明 |")
    md.append("|---|---:|---|")
    notes = {
        "store": "20 家门店，订单量呈头部效应",
        "product": "200 个商品（每店 10 个），其中 20 个从未售出",
        "customer": "5000 位顾客，其中 500 位从未下单",
        "rider": "200 位骑手，其中 20 位从未配送",
        "orders": "约 15% 尚未派单；状态与订单新旧相关",
        "order_item": "每单 1–5 条，商品必定与订单同店",
    }
    for t, c in counts.items():
        md.append(f"| `{t}` | {c:,} | {notes.get(t,'')} |")
    md.append("\n> 数据为**合成数据**（无真实运营数据可用）。生成脚本 `03_experiment_data.sql`。")
    md.append("> 伪随机来自 `SHA2()` 哈希而非 `RAND()`，重复执行可得到完全相同的数据集。")

    md.append("\n## 表 C 三种结构下的核心查询表现\n")
    md.append("| 查询 | A 基线 (ms) | C 加索引 (ms) | C 相对 A | B 无索引 (ms) | B 相对 A | A 访问计划 | C 访问计划 |")
    md.append("|---|---:|---:|---:|---:|---:|---|---|")

    def plan_str(m):
        return " → ".join(f"{p['table']}:{p['type']}({p['rows']})" for p in m["explain"])

    for name, _ in workload:
        a = results["A_reference_baseline"][name]
        c = results["C_optimized"][name]
        b = results["B_no_index"][name]
        if a["median_ms"] and c["median_ms"]:
            r_ac = (f"{a['median_ms']/c['median_ms']:.1f}x 快" if c["median_ms"] < a["median_ms"]
                    else f"{c['median_ms']/a['median_ms']:.2f}x 慢")
        else:
            r_ac = "-"
        r_ab = f"{b['median_ms']/a['median_ms']:.1f}x 慢" if a["median_ms"] else "-"
        md.append(f"| {name} | {a['median_ms']} | {c['median_ms']} | {r_ac} | "
                  f"{b['median_ms']} | {r_ab} | {plan_str(a)} | {plan_str(c)} |")

    md.append("\n> **访问计划写法**：`表:访问类型(估算行数)`，取自 `EXPLAIN FORMAT=TRADITIONAL`。")
    md.append("> `ALL` = 全表扫描；`ref` / `eq_ref` / `index` = 使用索引；带 `Using index` 表示覆盖索引，无需回表。")

    md.append("\n### 执行计划对比（结构 A vs C，Q1 门店销售额）\n")
    md.append("> 注：下表的结构化字段取自 "
              "`EXPLAIN FORMAT=TRADITIONAL`。\n")
    for key, label in [("A_reference_baseline", "A 基线"), ("C_optimized", "C 加索引")]:
        q1 = results[key]["Q1 门店销售额（经 order_item 汇总）"]
        md.append(f"**{label}** — 传统表格：")
        md.append("")
        md.append("| 表 | 访问类型 | 使用索引 | 估算行数 | 附加信息 |")
        md.append("|---|---|---|---:|---|")
        for p in q1["explain"]:
            md.append(f"| `{p['table']}` | {p['type']} | {p['key'] or '-'} | {p['rows']} | {p['Extra'] or '-'} |")
        md.append("")
        md.append(f"**{label}** — 树形计划（`EXPLAIN` 默认输出）：")
        md.append("")
        md.append("```text")
        md.append(q1["tree_plan"].rstrip())
        md.append("```")
        md.append("")

    md.append("\n## 表 D 写入与存储代价\n")
    md.append("| 指标 | A 基线 | C 加索引 | B 无索引 |")
    md.append("|---|---:|---:|---:|")

    def idx_count(key):
        return len([i for i in inventories[key] if i["table"] in ("orders", "order_item")])

    def idx_mb(key):
        return sum(s["index_mb"] for s in sizes[key])

    wa = writes["A_reference_baseline"]["median_s"]
    wc = writes["C_optimized"]["median_s"]
    wb = writes["B_no_index"]["median_s"]
    md.append(f"| `orders` + `order_item` 索引总数 | {idx_count('A_reference_baseline')} | "
              f"{idx_count('C_optimized')} | {idx_count('B_no_index')} |")
    md.append(f"| 批量插入 {WRITE_BATCH:,} 行明细耗时中位数 (s) | {wa} | {wc} | {wb} |")
    md.append(f"| 写入耗时相对 A 的变化 | — | {(wc-wa)/wa*100:+.1f}% | {(wb-wa)/wa*100:+.1f}% |")
    md.append(f"| 全库索引占用 (MB) | {idx_mb('A_reference_baseline'):.2f} | "
              f"{idx_mb('C_optimized'):.2f} | {idx_mb('B_no_index'):.2f} |")
    md.append("")

    md.append("### 每张表的空间占用（结构 A）\n")
    md.append("| 表 | 数据 (MB) | 索引 (MB) | 合计 (MB) |")
    md.append("|---|---:|---:|---:|")
    for s in sizes["A_reference_baseline"]:
        md.append(f"| `{s['table']}` | {s['data_mb']} | {s['index_mb']} | {s['total_mb']} |")

    md.append("\n### 索引清单（结构 A，共 %d 个）\n" % len(inventories["A_reference_baseline"]))
    md.append("| 表 | 索引 | 列 |")
    md.append("|---|---|---|")
    for i in inventories["A_reference_baseline"]:
        md.append(f"| `{i['table']}` | `{i['index']}` | {i['cols']} |")

    md.append("\n### 结构 C 新增的 4 条索引\n")
    md.append("| 索引 | 列 | 目标查询 |")
    md.append("|---|---|---|")
    for nm, cols, q in [
        ("ix_oi_pid_cover", "order_item(product_id, quantity, unit_price)", "Q1 门店销售额"),
        ("ix_oi_pid_oid", "order_item(product_id, order_id)", "Q3 买过指定商品的顾客"),
        ("ix_orders_cust_amt", "orders(customer_id, total_amount)", "Q4 每位顾客订单数与消费总额"),
        ("ix_orders_rider_st", "orders(rider_id, order_status, order_id)", "Q2 每位骑手配送量"),
    ]:
        md.append(f"| `{nm}` | {cols} | {q} |")

    md.append("\n> ⚠️ **本次实验的一个实测发现（值得单独写进报告）**：")
    md.append("> MySQL 在新索引能够替代外键自动索引时，会**自动删除原来的外键单列索引**。")
    md.append("> 因此在结构 A 上执行上述 4 条 `CREATE INDEX` 后，索引总数由 14 变为 "
              f"{len(inventories['C_optimized'])}（而不是 14+4=18）：")
    md.append("> `order_item.fk_item_product`、`orders.fk_order_customer`、`orders.fk_order_rider` "
              "三条单列外键索引被对应的复合索引取代并删除；外键**约束**本身仍然有效。")
    md.append("> 净效果是**新增 4 条复合索引、移除 3 条单列索引，净增 1 个索引**。")
    md.append("> 这也意味着回退时不能直接 `DROP INDEX`（会报 `ERROR 1553`），"
              "必须先删外键约束、再删索引、最后把外键加回来 —— 见 `04_indexes.sql` 的 `revert_optimized` 段。")

    out_md = os.path.join(RES_DIR, "RESULT_TABLES.md")
    io.open(out_md, "w", encoding="utf-8").write("\n".join(md) + "\n")

    json.dump({"environment": env, "row_counts": counts,
               "structures": {k: {"indexes": inventories[k], "sizes": sizes[k],
                                  "write_cost": writes[k], "queries": results[k]} for k in results}},
              io.open(os.path.join(RES_DIR, "all_results.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2, default=str)

    say(f"\n结果表已写入: {out_md}")
    conn.close()
    root.close()


if __name__ == "__main__":
    main()
