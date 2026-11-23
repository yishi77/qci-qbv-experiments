from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results"
OUTPUT.mkdir(exist_ok=True)


def read_scalars(path: Path) -> dict[tuple[str, str], float]:
    result: dict[tuple[str, str], float] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("scalar "):
            continue
        body = line[7:]
        try:
            module, body = body.split(" ", 1)
            if body.startswith('"'):
                end = body.find('"', 1)
                name = body[1:end]
                value = body[end + 1:].strip()
            else:
                name, value = body.split(" ", 1)
            result[(module, name)] = float(value)
        except (ValueError, IndexError):
            continue
    return result


def read_delays(path: Path) -> list[float]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    vector_id = None
    pattern = re.compile(r"^vector (\d+) QciQbvThreeSchemes\.server\.app\[1\] endToEndDelay")
    for line in lines:
        match = pattern.match(line)
        if match:
            vector_id = match.group(1)
            break
    if vector_id is None:
        return []
    values = []
    for line in lines:
        if line.startswith(vector_id + "\t"):
            fields = line.split("\t")
            if len(fields) >= 4:
                try:
                    values.append(float(fields[3]))
                except ValueError:
                    pass
    return values


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def one_row(path: Path) -> dict[str, object]:
    scalars = read_scalars(path)
    delays = read_delays(path.with_suffix(".vec"))
    source = "QciQbvThreeSchemes.stClient.app[0]"
    sink = "QciQbvThreeSchemes.server.app[1]"
    queue = "QciQbvThreeSchemes.switch.eth[2].macLayer.queue.queue[1]"
    gate = "QciQbvThreeSchemes.switch.bridging.streamFilter.ingress.gateFilter[0]"
    filter_path = "QciQbvThreeSchemes.switch.bridging.streamFilter.ingress.filter[0]"

    source_sent = int(scalars.get((source, "packets sent"), 0))
    delivered = int(scalars.get((sink, "packets received"), 0))
    source_admission_drop = int(scalars.get((source, "admission dropped frames"), 0))
    gate_drop = int(scalars.get((gate, "droppedPackets:count"), 0))
    filter_drop = int(scalars.get((filter_path, "droppedPackets:count"), 0))
    candidate = source_sent + source_admission_drop
    network_drop = max(0, source_sent - delivered)
    total_drop = source_admission_drop + network_drop
    row: dict[str, object] = {
        "config": path.stem.removesuffix("-#0"),
        "candidate_frames": candidate,
        "source_packets_sent": source_sent,
        "delivered": delivered,
        "dropped_total": total_drop,
        "source_admission_drop": source_admission_drop,
        "network_drop": network_drop,
        "gate_drop": gate_drop,
        "filter_drop": filter_drop,
        "flow_drop": int(scalars.get((source, "flow dropped frames"), 0)),
        "early_drop": int(scalars.get((source, "early dropped frames"), 0)),
        "deadline_drop": int(scalars.get((source, "deadline dropped frames"), 0)),
        "max_queue": int(scalars.get((queue, "queueLength:max"), 0)),
        "avg_queue": scalars.get((queue, "queueLength:timeavg"), 0.0),
        "mean_delay_s": scalars.get((sink, "mean end-to-end delay")),
        "max_delay_s": scalars.get((sink, "maximum end-to-end delay")),
        "p99_delay_s": percentile(delays, 0.99),
        "deadline_miss": sum(delay > 0.001 for delay in delays),
    }
    return row


def write_dataset(folder: str, output_stem: str, title: str, description: str, rows: list[dict[str, object]]) -> None:
    output_csv = OUTPUT / f"{output_stem}.csv"
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    def us(value: object) -> str:
        return "" if value is None else f"{float(value) * 1e6:.3f} us"

    lines = [f"# {title}", "", description, "", "| 配置 | 候选帧 | 源端发送 | 交付 | 丢弃 | 最大队列 | 平均队列 | 平均时延 | 最大时延 | P99 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in rows:
        lines.append(
            f"| {row['config']} | {row['candidate_frames']} | {row['source_packets_sent']} | {row['delivered']} | {row['dropped_total']} | "
            f"{row['max_queue']} | {float(row['avg_queue']):.3f} | {us(row['mean_delay_s'])} | {us(row['max_delay_s'])} | {us(row['p99_delay_s'])} |"
        )
    lines += ["", "## 丢弃分解", "", "| 配置 | 源端准入丢弃 | 网络丢弃 | Gate 丢弃 | Filter 丢弃 | Flow Meter 丢弃 | 早到丢弃 | Deadline 丢弃 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in rows:
        lines.append(
            f"| {row['config']} | {row['source_admission_drop']} | {row['network_drop']} | {row['gate_drop']} | {row['filter_drop']} | "
            f"{row['flow_drop']} | {row['early_drop']} | {row['deadline_drop']} |"
        )
    (OUTPUT / f"{output_stem}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(output_csv)


ablation_rows = [one_row(path) for path in sorted((ROOT / "results_ablation").glob("*.sca"))]
write_dataset(
    "results_ablation",
    "three_scheme_ablation_results",
    "实验四：入口功能消融实验",
    "五组配置分别保留 Flow Meter、时间戳、时间戳加序号、时间戳加 Flow Meter，以及完整 Proposed 组合。所有配置使用同一 mixed 扰动和 Qbv 参数。",
    ablation_rows,
)

drop_rows = [one_row(path) for path in sorted((ROOT / "results_drop_policy").glob("*.sca"))]
write_dataset(
    "results_drop_policy",
    "three_scheme_drop_policy_results",
    "实验五：主动丢弃策略实验",
    "比较不主动丢弃、超过 Deadline 丢弃，以及预计等待超过 MaxQueueDelay 或预计完成超过 Deadline 时丢弃。",
    drop_rows,
)

sensitivity_rows = [one_row(path) for path in sorted((ROOT / "results_sensitivity").glob("*.sca"))]
write_dataset(
    "results_sensitivity",
    "three_scheme_sensitivity_results",
    "实验六：参数敏感性实验",
    "扫描 EarlyTolerance、LateTolerance、Deadline、MaxQueueDelay 和 Flow Meter 突发阈值，观察交付、丢弃、队列和时延变化。",
    sensitivity_rows,
)
