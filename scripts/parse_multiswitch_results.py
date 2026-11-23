from __future__ import annotations

import csv
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results_multiswitch"
OUTPUT = ROOT / "results"
OUTPUT.mkdir(exist_ok=True)


def read_scalars(path: Path):
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


def read_delays(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    vector_id = None
    pattern = re.compile(r'^vector (\d+) QciQbvMultiSwitch\.server\.app\[1\] endToEndDelay')
    for line in lines:
        match = pattern.match(line)
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
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1))]


rows = []
for scheme, stem in [
    ("Qbv-only", "QbvOnly-#0"),
    ("Full-Qci+Qbv", "FullQciQbv-#0"),
    ("Clipped-Qci+Qbv", "ClippedQciQbv-#0"),
]:
    s = read_scalars(RESULTS / (stem + ".sca"))
    d = read_delays(RESULTS / (stem + ".vec"))
    source = "QciQbvMultiSwitch.stClient.app[0]"
    sink = "QciQbvMultiSwitch.server.app[1]"
    queue_paths = [
        "QciQbvMultiSwitch.switch1.eth[2].macLayer.queue.queue[1]",
        "QciQbvMultiSwitch.switch2.eth[1].macLayer.queue.queue[1]",
        "QciQbvMultiSwitch.switch3.eth[1].macLayer.queue.queue[1]",
    ]
    queue_max = max(int(s.get((path, "queueLength:max"), 0)) for path in queue_paths)
    queue_avg = sum(s.get((path, "queueLength:timeavg"), 0) for path in queue_paths)
    gate_drop = sum(
        int(s.get((f"QciQbvMultiSwitch.switch{i}.bridging.streamFilter.ingress.gateFilter[0]", "droppedPackets:count"), 0))
        for i in (1, 2, 3)
    )
    rows.append({
        "scheme": scheme,
        "planned_base_frames": int(s.get((source, "planned base frames"), 0)),
        "source_packets_sent": int(s.get((source, "packets sent"), 0)),
        "delivered": int(s.get((sink, "packets received"), 0)),
        "missing_input": int(s.get((source, "missing input frames"), 0)),
        "gate_dropped": gate_drop,
        "max_st_queue_any_hop": queue_max,
        "sum_st_queue_timeavg": queue_avg,
        "mean_delay_s": s.get((sink, "mean end-to-end delay")),
        "max_delay_s": s.get((sink, "maximum end-to-end delay")),
        "p99_delay_s": percentile(d, 0.99),
    })

csv_path = OUTPUT / "three_scheme_multiswitch_results.csv"
with csv_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

def us(value):
    return "" if value is None else f"{value * 1e6:.3f} us"

report_lines = [
    "# 三交换机三方案实验结果",
    "",
    "拓扑为 ST/NST 客户端接入 switch1，再串联 switch2、switch3，最后连接 server。周期、窗口、帧长、扰动和链路速率沿用原版配置。",
    "",
    "| 方案 | 源端发送 | 交付 | 丢弃 | 多跳ST最大队列 | 平均时延 | 最大时延 | P99 |",
    "|---|---:|---:|---:|---:|---:|---:|---:|",
]
for row in rows:
    report_lines.append(
        f"| {row['scheme']} | {row['source_packets_sent']} | {row['delivered']} | {row['gate_dropped']} | "
        f"{row['max_st_queue_any_hop']} | {us(row['mean_delay_s'])} | {us(row['max_delay_s'])} | {us(row['p99_delay_s'])} |"
    )
report_lines += [
    "",
    "相同配置下，三交换机路径增加了逐跳处理和出口门控等待，使端到端时延高于单交换机结果。",
    "原版单交换机配置和结果文件保持独立。",
]
report_path = OUTPUT / "three_scheme_multiswitch_report.md"
report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
print(csv_path)
print(report_path)
