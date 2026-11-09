"""08_make_figures.py — 报告用图表（矢量 + 位图）

生成两张图，均同时输出 SVG（矢量，报告首选）与 PNG（300 dpi 备用）：
  figures/fig1_query_performance     三种结构下 6 条核心查询的响应时间对比
  figures/fig2_write_and_space_cost  读收益 vs 写入与存储代价

标签使用英文，用于直接放进英文报告；如需中文版改 LABELS 即可。

数据来源: results/all_results.json（由 05_benchmark.py 生成）
"""
import io
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = r"G:\dphlearning\database\project"
RES_DIR = os.path.join(ROOT, "results")
FIG_DIR = os.path.join(RES_DIR, "figures")

# 查询名 -> 图表用英文短标签
LABELS = {
    "Q1 门店销售额（经 order_item 汇总）": "Q1\nRevenue\nper store",
    "Q2 每位骑手配送量（含零单骑手）": "Q2\nDeliveries\nper rider",
    "Q3 买过指定商品的顾客（子查询版）": "Q3\nBuyers\n(IN subquery)",
    "Q3' 买过指定商品的顾客（JOIN 版）": "Q3'\nBuyers\n(JOIN)",
    "Q4 每位顾客订单数与消费总额": "Q4\nOrders & spend\nper customer",
    "Q5 尚未派单的订单": "Q5\nOrders without\nrider",
}
# 结果表里的顺序就是工作负载顺序
ORDER = list(LABELS.keys())

STRUCTS = [
    ("A_reference_baseline", "A  Reference baseline (14 indexes)", "#4C72B0"),
    ("C_optimized",          "C  + 4 composite indexes (15)",       "#55A868"),
    ("B_no_index",           "B  No foreign-key indexes (9)",       "#C44E52"),
]


def load():
    return json.load(io.open(os.path.join(RES_DIR, "all_results.json"), encoding="utf-8"))


def style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.labelsize": 9,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linestyle": ":",
        "figure.dpi": 110,
        "savefig.bbox": "tight",
    })


def fig1(data):
    """三种结构下 6 条查询的响应时间（对数刻度 + 数值标签）。"""
    n_q = len(ORDER)
    x = np.arange(n_q)
    w = 0.26
    fig, ax = plt.subplots(figsize=(11, 5.2))

    for i, (key, label, color) in enumerate(STRUCTS):
        vals = [data["structures"][key]["queries"][q]["median_ms"] for q in ORDER]
        pos = x + (i - 1) * w
        bars = ax.bar(pos, vals, w, label=label, color=color, edgecolor="white", linewidth=0.6)
        for b, v in zip(bars, vals):
            ax.annotate(f"{v:.1f}", (b.get_x() + b.get_width() / 2, v),
                        textcoords="offset points", xytext=(0, 2),
                        ha="center", fontsize=7, rotation=0)

    ax.set_yscale("log")
    ax.set_ylabel("Median response time (ms, log scale)")
    ax.set_title("Query response time by index structure\n"
                 "Topic 2 Community Fresh-Food Next-Day Delivery — 50,000 orders / 150,152 order items",
                 pad=26)
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[q] for q in ORDER], fontsize=8)
    ax.set_ylim(2, 2600)
    # 图例放在坐标区上方一行，避免遮挡 Q1 的柱标签
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.005), ncol=3,
              frameon=False, fontsize=8, handlelength=1.4, columnspacing=1.6)
    ax.grid(axis="x", visible=False)

    fig.text(0.01, -0.02,
             "Median of 7 runs after 3 warm-up runs. MySQL Community Server 8.0.46, InnoDB, "
             "innodb_buffer_pool_size = 128 MiB.",
             fontsize=7, color="#555555")
    return fig


def fig2(data):
    """写入代价与索引空间（读收益的代价）。"""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    keys = [k for k, _, _ in STRUCTS]
    labels = ["A\nbaseline", "C\n+4 indexes", "B\nno FK idx"]
    colors = [c for _, _, c in STRUCTS]

    wc = [data["structures"][k]["write_cost"]["median_s"] for k in keys]
    idx_mb = [sum(s["index_mb"] for s in data["structures"][k]["sizes"]) for k in keys]

    for ax, vals, title, ylab, unit, fmt in [
        (axes[0], wc, "Bulk insert cost", "Elapsed time (s)", "s", "{:.3f}"),
        (axes[1], idx_mb, "Index storage", "Index size (MB)", "MB", "{:.2f}"),
    ]:
        bars = ax.bar(labels, vals, color=colors, width=0.55, edgecolor="white", linewidth=0.6)
        for b, v in zip(bars, vals):
            ax.annotate(f"{fmt.format(v)} {unit}", (b.get_x() + b.get_width() / 2, v),
                        textcoords="offset points", xytext=(0, 3), ha="center", fontsize=8)
        ax.set_title(title)
        ax.set_ylabel(ylab)
        ax.grid(axis="x", visible=False)
        ax.set_ylim(0, max(vals) * 1.22)

    # 标注相对基线增幅
    d_c = (wc[1] - wc[0]) / wc[0] * 100
    d_b = (wc[2] - wc[0]) / wc[0] * 100
    axes[0].text(0.5, 0.94, f"C vs A: {d_c:+.1f}%    B vs A: {d_b:+.1f}%",
                 transform=axes[0].transAxes, ha="center", fontsize=8, color="#333333",
                 bbox=dict(boxstyle="round,pad=0.3", fc="#F5F5F5", ec="#CCCCCC"))

    fig.suptitle("The price of the indexes: write and storage cost",
                 fontsize=11, fontweight="bold")
    fig.text(0.01, -0.03,
             "Left: inserting 150,000 rows into a table with the same index set as order_item. "
             "Right: index_length of all base tables.",
             fontsize=7, color="#555555")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return fig


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    os.makedirs(FIG_DIR, exist_ok=True)
    style()
    data = load()

    for name, fn in [("fig1_query_performance", fig1), ("fig2_write_and_space_cost", fig2)]:
        fig = fn(data)
        for ext in ("svg", "png"):
            p = os.path.join(FIG_DIR, f"{name}.{ext}")
            fig.savefig(p, format=ext, dpi=300)
            print("wrote", p)
        plt.close(fig)

    # 打印关键数字，便于正文引用
    print("\n--- 正文可引用的数字 ---")
    for key, label, _ in STRUCTS:
        q = data["structures"][key]["queries"]
        w = data["structures"][key]["write_cost"]
        mb = sum(s["index_mb"] for s in data["structures"][key]["sizes"])
        print(f"{label}: Q1={q[ORDER[0]]['median_ms']}ms  Q2={q[ORDER[1]]['median_ms']}ms  "
              f"write={w['median_s']}s  index={mb:.2f}MB")


if __name__ == "__main__":
    main()
