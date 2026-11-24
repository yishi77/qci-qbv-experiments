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
    flt = "QciQbvThreeSchemes.switch.bridging.streamFilter.ingress.filter[0]"

    source_sent = int(scalars.get((source, "base frames sent"), 0) + scalars.get((source, "insert frames sent"), 0))
    delivered = len(delays)
    return {
        "config": path.stem.removesuffix("-#0"),
        "source_packets_sent": source_sent,
        "delivered": delivered,
        "ingress_passed": int(scalars.get((flt, "passed packets"), 0)),
        "buffered": int(scalars.get((flt, "buffered packets"), 0)),
        "released_after_reorder": int(scalars.get((flt, "released after reorder"), 0)),
        "dropped_early": int(scalars.get((flt, "dropped early"), 0)),
        "dropped_flow": int(scalars.get((flt, "dropped flow"), 0)),
        "dropped_deadline": int(scalars.get((flt, "dropped deadline"), 0)),
        "dropped_duplicate": int(scalars.get((flt, "dropped duplicate"), 0)),
        "dropped_gap_timeout": int(scalars.get((flt, "dropped gap timeout"), 0)),
        "dropped_reorder_buffer": int(scalars.get((flt, "dropped reorder buffer"), 0)),
        "max_queue": int(scalars.get((queue, "queueLength:max"), 0)),
        "avg_queue": scalars.get((queue, "queueLength:timeavg"), 0.0),
        "mean_delay_s": scalars.get((sink, "mean end-to-end delay")),
        "max_delay_s": scalars.get((sink, "maximum end-to-end delay")),
        "p99_delay_s": percentile(delays, 0.99),
    }


def main() -> None:
    rows = [one_row(path) for path in sorted((ROOT / "results_exp7").glob("*.sca"))]
    if not rows:
        raise SystemExit("No .sca files found in results_exp7")

    output_csv = OUTPUT / "exp7_ingress_results.csv"
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    def us(value: object) -> str:
        return "" if value is None else f"{float(value) * 1e6:.3f} us"

    lines = [
        "# 实验七：交换机入口版 Clipped-Qci + ReorderTimeout 验证",
        "",
        "将自定义时间准入模块下沉至交换机入口（`ClippedQciIngressFilter`），在裁剪 PSFP 周期流门控表的前提下结合 VLAN 分类、标准 Flow Meter、早到暂存、纯序号查重、窗口剩余时间预测与 `ReorderTimeout` 丢帧确认。",
        "",
        "| 配置 | 源端发送 | 交付 | 入口放行 | 暂存 | 重排释放 | 早到丢弃 | 突发丢弃 | Deadline 丢弃 | 重复丢弃 | 缺口超时 | 最大队列 | 平均队列 | 平均时延 | 最大时延 | P99 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['config']} | {row['source_packets_sent']} | {row['delivered']} | {row['ingress_passed']} | "
            f"{row['buffered']} | {row['released_after_reorder']} | {row['dropped_early']} | {row['dropped_flow']} | "
            f"{row['dropped_deadline']} | {row['dropped_duplicate']} | {row['dropped_gap_timeout']} | "
            f"{row['max_queue']} | {float(row['avg_queue']):.3f} | {us(row['mean_delay_s'])} | {us(row['max_delay_s'])} | {us(row['p99_delay_s'])} |"
        )
    (OUTPUT / "exp7_ingress_results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(output_csv)


if __name__ == "__main__":
    main()
