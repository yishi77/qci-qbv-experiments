from __future__ import annotations

import csv
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results_backlog"
OUTPUT = ROOT / "results"
OUTPUT.mkdir(exist_ok=True)


def scalars(path: Path):
    result = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("scalar "):
            continue
        body = line[7:]
        path_name, body = body.split(" ", 1)
        if body.startswith('"'):
            end = body.find('"', 1)
            name = body[1:end]
            value = body[end + 1:].strip()
        else:
            name, value = body.split(" ", 1)
        try:
            result[(path_name, name)] = float(value)
        except ValueError:
            pass
    return result


def delays(path: Path):
    vector_id = None
    header = re.compile(r'^vector (\d+) QciQbvThreeSchemes\.server\.app\[1\] endToEndDelay')
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines:
        match = header.match(line)
        if match:
            vector_id = match.group(1)
            break
    if vector_id is None:
        return []
    return [
        float(line.split("\t")[3])
        for line in lines
        if line.startswith(vector_id + "\t") and len(line.split("\t")) >= 4
    ]


def percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return None
    return ordered[max(0, min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1))]


rows = []
for scheme, stem in [
    ("Qbv-only", "BacklogQbvOnly-#0"),
    ("Full-Qci+Qbv", "BacklogFullQciQbv-#0"),
    ("Clipped-Qci+Qbv", "BacklogClippedQciQbv-#0"),
]:
    s = scalars(RESULTS / (stem + ".sca"))
    d = delays(RESULTS / (stem + ".vec"))
    source = "QciQbvThreeSchemes.stClient.app[0]"
    sink = "QciQbvThreeSchemes.server.app[1]"
    queue = "QciQbvThreeSchemes.switch.eth[2].macLayer.queue.queue[1]"
    gate = "QciQbvThreeSchemes.switch.bridging.streamFilter.ingress.gateFilter[0]"
    filt = "QciQbvThreeSchemes.switch.bridging.streamFilter.ingress.filter[0]"
    rows.append({
        "scheme": scheme,
        "planned_base_frames": int(s.get((source, "planned base frames"), 0)),
        "source_packets_sent": int(s.get((source, "packets sent"), 0)),
        "delivered": int(s.get((sink, "packets received"), 0)),
        "source_admission_dropped": int(s.get((source, "admission dropped frames"), 0)),
        "source_filter_dropped": int(s.get((source, "filter dropped frames"), 0)),
        "deadline_dropped": int(s.get((source, "deadline dropped frames"), 0)),
        "full_gate_dropped": int(s.get((gate, "droppedPackets:count"), 0)),
        "full_filter_dropped": int(s.get((filt, "droppedPackets:count"), 0)),
        "max_queue": int(s.get((queue, "queueLength:max"), 0)),
        "avg_queue": s.get((queue, "queueLength:timeavg")),
        "mean_delay_s": s.get((sink, "mean end-to-end delay")),
        "max_delay_s": s.get((sink, "maximum end-to-end delay")),
        "p99_delay_s": percentile(d, 0.99),
    })

csv_path = OUTPUT / "three_scheme_backlog_results.csv"
with csv_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

report_path = OUTPUT / "three_scheme_backlog_report.md"
def us(value):
    return "" if value is None else f"{value * 1e6:.3f} us"

lines = [
    "# 三方案帧积压压力实验",
    "",
    "原始 `omnetpp.ini` 保持不变。本实验使用独立的 `omnetpp_backlog.ini`。",
    "每个 1 ms 周期生成 1 个基础 ST 帧和 15 个额外插入帧，Qbv ST 窗口保持 100 us，仿真时间为 800 ms。",
    "",
    "| 方案 | 源端发送 | 交付 | 丢弃 | 最大队列 | 平均队列 | 平均时延 | 最大时延 | P99 |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
]
for row in rows:
    dropped = row["source_admission_dropped"] + row["full_gate_dropped"] + row["full_filter_dropped"]
    lines.append(
        f"| {row['scheme']} | {row['source_packets_sent']} | {row['delivered']} | {dropped} | "
        f"{row['max_queue']} | {row['avg_queue']:.3f} | {us(row['mean_delay_s'])} | "
        f"{us(row['max_delay_s'])} | {us(row['p99_delay_s'])} |"
    )
lines += [
    "",
    "Qbv-only 让全部 3200 个 ST 帧进入出口队列，队列达到明显积压。Full-Qci 使用入口门控和监管过滤额外帧，Clipped-Qci 在发送端准入模块中过滤额外帧。",
    "",
    "该压力配置用于观察过载条件下的机制差异，原始基线配置和结果保持独立。",
]
report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(csv_path)
print(report_path)
