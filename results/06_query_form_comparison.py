"""06_query_form_comparison.py — 老师第 4 题：同一查询的三种写法性能对比

问题原文:
  For "find users who bought a product of category X", how would you write it
  with a subquery versus a JOIN? Which is usually more efficient, and why?

本项目对应查询: "买过指定商品的顾客"

对比三种写法:
  V1  IN 子查询       （提交版 Select_Part 中的子查询写法）
  V2  JOIN + DISTINCT （提交版 Select_Part 中的 JOIN 写法）
  V3  EXISTS 半连接   （答案 key 提到 "EXISTS (a semi-join) is often even better than IN"）

严谨性保证:
  * 三种写法必须返回**完全相同的结果集**，否则性能对比无意义 —— 脚本会逐一断言
  * 在结构 A（基线）和结构 C（加索引）下各测一遍，说明"写法"与"索引"哪个影响更大
  * 选取不同选择性的商品，避免只测一个特例

输出: results/QUERY_FORM_COMPARISON.md
"""
import io
import json
import os
import statistics
import sys
import time

import mysql.connector as mc

DB = "fresh_delivery"
CFG = dict(host="127.0.0.1", port=3306, user="root", password="", database=DB)
ROOT = r"G:\dphlearning\database\project"
SQL_DIR = os.path.join(ROOT, "sql")
RES_DIR = os.path.join(ROOT, "results")
WARMUP, RUNS = 3, 7

V1_IN = """SELECT c.customer_id, c.customer_name, c.phone
FROM customer c
WHERE c.customer_id IN (
    SELECT o.customer_id
    FROM orders o
    JOIN order_item oi ON oi.order_id = o.order_id
    WHERE oi.product_id = {p} AND o.order_status <> 'cancelled')"""

V2_JOIN = """SELECT DISTINCT c.customer_id, c.customer_name, c.phone
FROM customer c
JOIN orders o      ON c.customer_id = o.customer_id
JOIN order_item oi ON oi.order_id   = o.order_id
WHERE oi.product_id = {p} AND o.order_status <> 'cancelled'"""

V3_EXISTS = """SELECT c.customer_id, c.customer_name, c.phone
FROM customer c
WHERE EXISTS (
    SELECT 1
    FROM orders o
    JOIN order_item oi ON oi.order_id = o.order_id
    WHERE o.customer_id = c.customer_id
      AND oi.product_id = {p}
      AND o.order_status <> 'cancelled')"""

VARIANTS = [("V1 IN 子查询", V1_IN), ("V2 JOIN + DISTINCT", V2_JOIN), ("V3 EXISTS 半连接", V3_EXISTS)]


def read(p):
    # utf-8-sig：SQL 文件带 UTF-8 BOM（为了让 Workbench 正确识别中文注释），
    # 用 utf-8-sig 读取会把 BOM 剥掉，否则它会混进第一条语句里。
    return io.open(p, encoding="utf-8-sig").read()


def split_sql(text):
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
    text = read(path)
    parts, cur, name = {}, [], None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("-- ### SECTION:"):
            if name:
                parts[name] = "\n".join(cur)
            name = s.split(":", 1)[1].split("->")[0].strip()
            cur = []
            continue
        if name is not None:
            cur.append(line)
    if name:
        parts[name] = "\n".join(cur)
    return parts


def run_sql(conn, text):
    cur = conn.cursor()
    for stmt in split_sql(text):
        cur.execute(stmt)
        try:
            cur.fetchall()
        except Exception:
            pass
        try:
            while cur.nextset():
                cur.fetchall()
        except Exception:
            pass


def has_index(conn, table, index):
    cur = conn.cursor()
    cur.execute("""SELECT COUNT(*) FROM information_schema.STATISTICS
                   WHERE table_schema=%s AND table_name=%s AND index_name=%s""",
                (DB, table, index))
    return cur.fetchone()[0] > 0


def revert_if_needed(conn, sec):
    """只有在结构 C 的索引确实存在时才回退，避免 DROP 不存在的索引报 1091。"""
    if has_index(conn, "order_item", "ix_oi_pid_cover"):
        run_sql(conn, sec["revert_optimized"])


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
    cur.execute("EXPLAIN " + sql)
    tree = "\n".join(str(r[0]) for r in cur.fetchall())
    return {"median": round(statistics.median(times), 3),
            "min": round(min(times), 3), "max": round(max(times), 3),
            "all": [round(t, 3) for t in times], "tree": tree}


def main():
    os.makedirs(RES_DIR, exist_ok=True)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # 从干净的 schema + 数据重建实验库，不依赖上一次运行留下的状态
    root = mc.connect(host=CFG["host"], port=CFG["port"], user=CFG["user"], password=CFG["password"])
    rc = root.cursor()
    rc.execute(f"DROP DATABASE IF EXISTS {DB}")
    rc.execute(f"CREATE DATABASE {DB} DEFAULT CHARSET=utf8mb4")
    conn = mc.connect(**CFG)
    conn.autocommit = True
    run_sql(conn, read(os.path.join(SQL_DIR, "01_schema.sql")))
    run_sql(conn, read(os.path.join(SQL_DIR, "03_experiment_data.sql")))
    print("实验库已重建（5 万订单）")

    cur = conn.cursor()

    # 选取三种不同选择性的商品：让结果集规模有差异，避免只测特例
    cur.execute("""SELECT oi.product_id, COUNT(DISTINCT o.customer_id) AS buyers
                   FROM order_item oi JOIN orders o ON oi.order_id = o.order_id
                   WHERE o.order_status <> 'cancelled'
                   GROUP BY oi.product_id ORDER BY buyers DESC""")
    rows = cur.fetchall()
    picks = [("高选择性（买家最多）", rows[0][0]),
             ("中位选择性", rows[len(rows)//2][0]),
             ("低选择性（买家最少）", rows[-1][0])]
    print("测试商品:", picks)

    sec = sections(os.path.join(SQL_DIR, "04_indexes.sql"))
    report = {}
    out = []

    for struct_key, struct_label, applies in [
        ("A", "结构 A · 参考基线", []),
        ("C", "结构 C · 加 4 条业务索引", ["apply_optimized"]),
    ]:
        # 每次切回结构 A 再按需加索引
        revert_if_needed(conn, sec)
        for a in applies:
            run_sql(conn, sec[a])
        run_sql(conn, "ANALYZE TABLE customer, orders, order_item")
        time.sleep(0.3)

        out.append(f"\n## {struct_label}\n")
        report[struct_key] = {}
        for sel_label, pid in picks:
            sqls = [(nm, tpl.format(p=pid)) for nm, tpl in VARIANTS]
            # 断言三种写法结果集完全相同
            sets = []
            for nm, s in sqls:
                cur.execute(s)
                sets.append(sorted(tuple(r) for r in cur.fetchall()))
            same = all(x == sets[0] for x in sets)
            out.append(f"### 商品 `product_id = {pid}`（{sel_label}，买家 {len(sets[0])} 人）\n")
            out.append("| 写法 | 中位数 (ms) | 最快 (ms) | 最慢 (ms) | 结果行数 | 与其它写法结果一致 |")
            out.append("|---|---:|---:|---:|---:|:--:|")
            res = {}
            for (nm, s), st in zip(sqls, sets):
                m = measure(conn, s)
                m["rows"] = len(st)
                res[nm] = m
                out.append(f"| {nm} | {m['median']} | {m['min']} | {m['max']} | {len(st)} | {'✅' if same else '❌'} |")
            report[struct_key][pid] = res
            base = res["V1 IN 子查询"]["median"]
            out.append("")
            out.append(f"- **V1 IN 子查询** = 基准（{base} ms）")
            for nm in ("V2 JOIN + DISTINCT", "V3 EXISTS 半连接"):
                r = res[nm]["median"]
                if base and r:
                    if r < base:
                        out.append(f"- **{nm}**：比基准**快 {base/r:.2f}×**（{r} ms）")
                    else:
                        out.append(f"- **{nm}**：比基准**慢 {r/base:.2f}×**（{r} ms）")
            out.append("")
            out.append(f"**V1 执行计划**（商品 {pid}）：")
            out.append("")
            out.append("```text")
            out.append(res["V1 IN 子查询"]["tree"].rstrip())
            out.append("```")
            out.append("")
            if not same:
                print(f"[警告] 商品 {pid} 三种写法结果集不一致！")

    # 恢复结构 A
    revert_if_needed(conn, sec)
    run_sql(conn, "ANALYZE TABLE customer, orders, order_item")

    header = [
        "# 老师第 4 题 · 同一查询三种写法的性能对比",
        "",
        "> 对应查询：**买过指定商品的顾客**（老师 Topic 2 示例查询 3）",
        "> 数据：`fresh_delivery`，5 万订单 / 150,152 条明细（结构 A 的 14 个索引）",
        f"> 测量协议：warm-up {WARMUP} 次，正式测量 {RUNS} 次，报告中位数",
        "",
        "## 三种写法",
        "",
        "| 变体 | 写法 | 来源 |",
        "|---|---|---|",
        "| V1 | `WHERE customer_id IN (SELECT ...)` | 提交版 `Select_Part_LUO Yipeng(4).sql` |",
        "| V2 | `JOIN` + `DISTINCT` | 同上 |",
        "| V3 | `WHERE EXISTS (SELECT 1 ...)` | 老师 Answer Key 第 4 题提到 `EXISTS` 半连接常优于 `IN` |",
        "",
        "> **前提**：三种写法在每组测试中都返回**完全相同的结果集**（脚本逐组断言），",
        "> 否则性能对比没有意义。",
    ]
    txt = "\n".join(header + out)
    p = os.path.join(RES_DIR, "QUERY_FORM_COMPARISON.md")
    io.open(p, "w", encoding="utf-8").write(txt + "\n")
    json.dump(report, io.open(os.path.join(RES_DIR, "query_form_comparison.json"), "w",
                              encoding="utf-8"), ensure_ascii=False, indent=2)
    print("wrote", p)
    conn.close()
    root.close()


if __name__ == "__main__":
    main()
