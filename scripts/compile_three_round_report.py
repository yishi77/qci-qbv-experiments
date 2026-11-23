from __future__ import annotations

import csv
from pathlib import Path

root = Path(__file__).resolve().parents[1]
results = root / "results"
results.mkdir(exist_ok=True)

rows = []
with (results / "three_scheme_omnet_results.csv").open(encoding="utf-8") as f:
    for row in csv.DictReader(f):
        rows.append({
            "round": "baseline",
            "scheme": row["scheme"],
            "source_sent": int(row["source_packets_sent"]),
            "delivered": int(row["delivered"]),
            "drop": int(row["network_or_qci_drop"]),
            "max_queue": int(row["max_st_queue"]),
            "avg_queue": "",
            "mean_delay_us": float(row["mean_delay_s"]) * 1e6,
            "max_delay_us": float(row["max_delay_s"]) * 1e6,
            "p99_us": float(row["p99_delay_s"]) * 1e6,
            "deadline_miss": int(row["deadline_miss"]),
        })

with (results / "three_scheme_backlog_results.csv").open(encoding="utf-8") as f:
    for row in csv.DictReader(f):
        rows.append({
            "round": "backlog",
            "scheme": row["scheme"],
            "source_sent": int(row["source_packets_sent"]),
            "delivered": int(row["delivered"]),
            "drop": int(row["source_admission_dropped"]) + int(row["full_gate_dropped"]) + int(row["full_filter_dropped"]),
            "max_queue": int(row["max_queue"]),
            "avg_queue": float(row["avg_queue"]),
            "mean_delay_us": float(row["mean_delay_s"]) * 1e6,
            "max_delay_us": float(row["max_delay_s"]) * 1e6,
            "p99_us": float(row["p99_delay_s"]) * 1e6 if row["p99_delay_s"] else "",
            "deadline_miss": "",
        })

with (results / "three_scheme_multiswitch_results.csv").open(encoding="utf-8") as f:
    for row in csv.DictReader(f):
        rows.append({
            "round": "multiswitch",
            "scheme": row["scheme"],
            "source_sent": int(row["source_packets_sent"]),
            "delivered": int(row["delivered"]),
            "drop": int(row["gate_dropped"]),
            "max_queue": int(row["max_st_queue_any_hop"]),
            "avg_queue": float(row["sum_st_queue_timeavg"]),
            "mean_delay_us": float(row["mean_delay_s"]) * 1e6,
            "max_delay_us": float(row["max_delay_s"]) * 1e6,
            "p99_us": float(row["p99_delay_s"]) * 1e6,
            "deadline_miss": "",
        })

comparison_csv = results / "three_round_comparison.csv"
with comparison_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

def find(round_name, scheme):
    return next(row for row in rows if row["round"] == round_name and row["scheme"] == scheme)

baseline_qbv = find("baseline", "Qbv-only")
multi_qbv = find("multiswitch", "Qbv-only")
baseline_full = find("baseline", "Full-Qci+Qbv")
multi_full = find("multiswitch", "Full-Qci+Qbv")
baseline_clip = find("baseline", "Clipped-Qci+Qbv")
multi_clip = find("multiswitch", "Clipped-Qci+Qbv")

report = results / "three_round_comparison_report.md"
def format_p99(value):
    return "" if value == "" else f"{value:.3f} us"

def format_row(row):
    return (
        f"| {row['round']} | {row['scheme']} | {row['source_sent']} | {row['delivered']} | "
        f"{row['drop']} | {row['max_queue']} | {row['mean_delay_us']:.3f} us | "
        f"{row['max_delay_us']:.3f} us | {format_p99(row['p99_us'])} |"
    )

report.write_text(
    """# 三轮实验综合对比与方案可行性分析

## 实验组织

原版配置保存在 `omnetpp.ini`，结果写入 `results_baseline`。压力配置使用 `omnetpp_backlog.ini`，结果写入 `results_backlog`。三交换机配置使用 `omnetpp_multiswitch.ini`，结果写入 `results_multiswitch`。三轮配置都调用同一套三方案代码。

## 核心结果

| 轮次 | 方案 | 源端发送 | 交付 | 丢弃 | 最大队列 | 平均时延 | 最大时延 | P99 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
"""
    + "\n".join(format_row(row) for row in rows)
    + """

## 结果判断

基础实验中，Qbv-only 保留了进入网络的帧，但产生了最大的平均时延、最大时延和 Deadline Miss。Full-Qci+Qbv 把窗口外帧过滤在入口，Clipped-Qci+Qbv 通过时间准入和 Deadline 判断保留了更多仍有业务价值的帧。

压力实验中，每个周期额外注入 15 个插入帧。Qbv-only 的 ST 队列达到 1001 帧，平均队列长度为 182.061，最大时延达到 91.094 ms。Full-Qci+Qbv 和 Clipped-Qci+Qbv 都把交付数量限制在 200 个基础帧，队列没有持续增长。这验证了入口准入是抑制过载积压的必要条件。

三交换机实验中，三种方案的交付数量与基础实验一致，端到端时延整体增加约 17 us。Qbv-only 的最大时延达到 1025.542 us，Full-Qci+Qbv 和 Clipped-Qci+Qbv 仍保持较低尾部时延。当前多跳配置没有加入额外同步偏差和传播时延，因此结果主要反映逐跳处理和门控等待。

## 方案可行性

### Qbv-only

能够提供出口时隙约束和完整帧边界，能够在正常负载下工作。过载时会保留异常帧并形成持续积压，最大时延和 P99 快速恶化，适合作为基线方案。

### Full-Qci+Qbv

能够用 Stream Filter、Stream Gate 和 Flow Meter 把过载帧限制在入口，压力实验中的队列保持稳定。当前实现仍需要补充序号检查和重复帧过滤，否则窗口内插入帧可能通过。多跳场景还需要校准每一跳 GCL 相位和同步误差。

### Clipped-Qci+Qbv

在基础、压力和多跳实验中都保持了较低的最大时延，并且比 Full-Qci 保留更多帧。当前时间准入模块位于发送端应用边界，后续应移动到交换机入口，形成独立的 TimingStateEvaluator 和 AdmissionController。该方案适合“控制最大时延、保证新鲜帧优先”的研究目标。

## 修订后的实施重点

1. 把正常帧交付率、异常帧过滤率、Deadline Miss 和过期帧比例分开统计。
2. 在 Full-Qci 中增加序号状态机，区分流量监管和重复帧检查。
3. 将 Clipped-Qci 的时间判断移动到交换机入口，并按每跳剩余 Deadline 重新计算预计完成时间。
4. 在多交换机实验中加入每跳传播时延、GCL 相位差和 gPTP 同步误差。
5. 使用独立结果目录和固定配置记录，继续进行不同负载、帧长、ST 流数量和随机种子的重复实验。
""",
    encoding="utf-8",
)
print(comparison_csv)
print(report)
