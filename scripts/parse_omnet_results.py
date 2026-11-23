from __future__ import annotations

import csv
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results_baseline"
OUTPUT = ROOT / "results"
OUTPUT.mkdir(exist_ok=True)


def read_scalars(path: Path) -> dict[tuple[str, str], float]:
    result = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("scalar "):
            continue
        rest = line[7:]
        try:
            path_part, rest = rest.split(" ", 1)
            if rest.startswith('"'):
                end_quote = rest.find('"', 1)
                name = rest[1:end_quote]
                value = rest[end_quote + 1:].strip()
            else:
                name, value = rest.split(" ", 1)
            result[(path_part, name)] = float(value.strip())
        except (ValueError, IndexError):
            continue
    return result


def read_delay_vector(path: Path) -> list[float]:
    vector_id = None
    header = re.compile(r'^vector (\d+) QciQbvThreeSchemes\.server\.app\[1\] endToEndDelay')
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = header.match(line)
        if match:
            vector_id = match.group(1)
            break
    if vector_id is None:
        return []

    values = []
    prefix = vector_id + "\t"
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            fields = line.split("\t")
            if len(fields) >= 4:
                values.append(float(fields[3]))
    return values


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


rows = []
for scheme, filename in [
    ("Qbv-only", "QbvOnly-#0"),
    ("Full-Qci+Qbv", "FullQciQbv-#0"),
    ("Clipped-Qci+Qbv", "ClippedQciQbv-#0"),
]:
    scalars = read_scalars(RESULTS / f"{filename}.sca")
    delays = read_delay_vector(RESULTS / f"{filename}.vec")
    source = "QciQbvThreeSchemes.stClient.app[0]"
    sink = "QciQbvThreeSchemes.server.app[1]"
    gate_filter = "QciQbvThreeSchemes.switch.bridging.streamFilter.ingress.gateFilter[0]"
    queue = "QciQbvThreeSchemes.switch.eth[2].macLayer.queue.queue[1]"

    sent = int(scalars.get((source, "packets sent"), 0))
    received = int(scalars.get((sink, "packets received"), 0))
    rows.append({
        "scheme": scheme,
        "scenario": "mixed",
        "planned_frames": int(scalars.get((source, "planned base frames"), 0)),
        "missing_input": int(scalars.get((source, "missing input frames"), 0)),
        "source_packets_sent": sent,
        "delivered": received,
        "network_or_qci_drop": sent - received,
        "clipped_admission_drop": int(scalars.get((source, "admission dropped frames"), 0)),
        "clipped_filter_drop": int(scalars.get((source, "filter dropped frames"), 0)),
        "clipped_deadline_drop": int(scalars.get((source, "deadline dropped frames"), 0)),
        "full_stream_gate_drop": int(scalars.get((gate_filter, "droppedPackets:count"), 0)),
        "max_st_queue": int(scalars.get((queue, "queueLength:max"), 0)),
        "mean_delay_s": scalars.get((sink, "mean end-to-end delay")),
        "max_delay_s": scalars.get((sink, "maximum end-to-end delay")),
        "min_delay_s": scalars.get((sink, "minimum end-to-end delay")),
        "p99_delay_s": percentile(delays, 0.99),
        "p999_delay_s": percentile(delays, 0.999),
        "deadline_miss": sum(delay > 0.001 for delay in delays),
    })

result_csv = OUTPUT / "three_scheme_omnet_results.csv"
with result_csv.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

report = OUTPUT / "three_scheme_omnet_report.md"
lines = [
    "# OMNeT++ 三方案实验结果",
    "",
    "本轮三套配置统一使用 mixed 扰动，周期 1 ms，Qbv ST 窗口为每周期最后 100 us，链路速率为 1 Gbit/s。",
    "",
    "| 方案 | 输入缺失 | 源端发送 | 交付 | 丢弃 | 最大队列 | 平均时延 | 最大时延 | P99 | Deadline Miss |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
]
for row in rows:
    def us(value: float | None) -> str:
        return "" if value is None else f"{value * 1e6:.3f} us"

    lines.append(
        f"| {row['scheme']} | {row['missing_input']} | {row['source_packets_sent']} | "
        f"{row['delivered']} | {row['network_or_qci_drop']} | {row['max_st_queue']} | {us(row['mean_delay_s'])} | "
        f"{us(row['max_delay_s'])} | {us(row['p99_delay_s'])} | {row['deadline_miss']} |"
    )

lines += [
    "",
    "## 入口统计",
    "",
    "- Full-Qci+Qbv 的 Stream Gate 丢弃数从 INET 的 gateFilter 统计中读取。",
    "- Clipped-Qci+Qbv 的入口丢弃数由自定义 TimingAdmissionUdpSourceApp 记录，该模块位于 ST 发送端应用边界，用于模拟裁剪后的入口准入逻辑。",
    "- Qbv-only 保留所有生成帧，插帧和晚到帧由 Qbv 队列继续处理。",
    "",
    "## 运行说明",
    "",
    "三套仿真均在 Ubuntu 虚拟机中的 OMNeT++ 6.4.0 和 INET 4.7.0 上以 Cmdenv 成功结束。",
    "当前结果用于验证三种方案的网络级接线和入口行为，后续可以加入更多 ST 流、更多交换机、同步误差和参数扫描。",
]
report.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(result_csv)
print(report)
