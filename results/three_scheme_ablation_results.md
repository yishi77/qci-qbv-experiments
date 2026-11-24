# 实验四：入口功能消融实验

五组配置分别保留 Flow Meter、时间戳、时间戳加序号、时间戳加 Flow Meter，以及完整 Proposed 组合。所有配置使用同一 mixed 扰动和 Qbv 参数。

| 配置 | 候选帧 | 源端发送 | 交付 | 丢弃 | 最大队列 | 平均队列 | 平均时延 | 最大时延 | P99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| AblationFlowMeterOnly | 198 | 188 | 188 | 10 | 1 | 0.181 | 336.982 us | 1008.482 us | 1008.482 us |
| AblationProposed | 198 | 127 | 127 | 71 | 1 | 0.009 | 14.449 us | 16.996 us | 16.996 us |
| AblationTimestampFlow | 198 | 127 | 127 | 71 | 1 | 0.009 | 14.449 us | 16.996 us | 16.996 us |
| AblationTimestampOnly | 198 | 137 | 137 | 61 | 1 | 0.009 | 15.259 us | 25.556 us | 25.556 us |
| AblationTimestampSequence | 198 | 127 | 127 | 71 | 1 | 0.009 | 14.449 us | 16.996 us | 16.996 us |

## 丢弃分解

| 配置 | 源端准入丢弃 | 网络丢弃 | Gate 丢弃 | Filter 丢弃 | Flow Meter 丢弃 | 早到丢弃 | Deadline 丢弃 |
|---|---:|---:|---:|---:|---:|---:|---:|
| AblationFlowMeterOnly | 10 | 0 | 0 | 0 | 10 | 0 | 0 |
| AblationProposed | 71 | 0 | 0 | 10 | 0 | 0 | 61 |
| AblationTimestampFlow | 71 | 0 | 0 | 0 | 10 | 0 | 61 |
| AblationTimestampOnly | 61 | 0 | 0 | 0 | 0 | 0 | 61 |
| AblationTimestampSequence | 71 | 0 | 0 | 10 | 0 | 0 | 61 |
