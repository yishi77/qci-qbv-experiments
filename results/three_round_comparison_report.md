# 三轮实验综合对比与方案可行性分析

## 实验组织

原版配置保存在 `omnetpp.ini`，结果写入 `results_baseline`。压力配置使用 `omnetpp_backlog.ini`，结果写入 `results_backlog`。三交换机配置使用 `omnetpp_multiswitch.ini`，结果写入 `results_multiswitch`。三轮配置都调用同一套三方案代码。

## 核心结果

| 轮次 | 方案 | 源端发送 | 交付 | 丢弃 | 最大队列 | 平均时延 | 最大时延 | P99 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | Qbv-only | 198 | 198 | 0 | 1 | 321.254 us | 1008.482 us | 1008.482 us |
| baseline | Full-Qci+Qbv | 198 | 99 | 99 | 1 | 17.861 us | 25.556 us | 25.556 us |
| baseline | Clipped-Qci+Qbv | 127 | 127 | 0 | 1 | 14.449 us | 16.996 us | 16.996 us |
| backlog | Qbv-only | 3200 | 3200 | 0 | 1001 | 45596.448 us | 91093.762 us | 90059.650 us |
| backlog | Full-Qci+Qbv | 3200 | 200 | 3000 | 1 | 16.996 us | 16.996 us | 16.996 us |
| backlog | Clipped-Qci+Qbv | 200 | 200 | 3000 | 1 | 16.996 us | 16.996 us | 16.996 us |
| multiswitch | Qbv-only | 198 | 198 | 0 | 1 | 338.320 us | 1025.542 us | 1025.542 us |
| multiswitch | Full-Qci+Qbv | 198 | 99 | 99 | 1 | 34.921 us | 42.616 us | 42.616 us |
| multiswitch | Clipped-Qci+Qbv | 127 | 127 | 0 | 1 | 31.509 us | 34.056 us | 34.056 us |

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
