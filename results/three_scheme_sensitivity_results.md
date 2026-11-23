# 实验六：参数敏感性实验

扫描 EarlyTolerance、LateTolerance、Deadline、MaxQueueDelay 和 Flow Meter 突发阈值，观察交付、丢弃、队列和时延变化。

| 配置 | 候选帧 | 源端发送 | 交付 | 丢弃 | 最大队列 | 平均队列 | 平均时延 | 最大时延 | P99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SensitivityBurst1 | 198 | 127 | 127 | 71 | 1 | 0.009 | 14.449 us | 16.996 us | 16.996 us |
| SensitivityBurst2 | 198 | 137 | 137 | 61 | 1 | 0.009 | 15.259 us | 25.556 us | 25.556 us |
| SensitivityBurst4 | 198 | 137 | 137 | 61 | 1 | 0.009 | 15.259 us | 25.556 us | 25.556 us |
| SensitivityDeadline1m | 198 | 137 | 137 | 61 | 1 | 0.009 | 15.259 us | 25.556 us | 25.556 us |
| SensitivityDeadline2m | 198 | 198 | 198 | 0 | 1 | 0.181 | 321.254 us | 1008.482 us | 1008.482 us |
| SensitivityDeadline500u | 198 | 137 | 137 | 61 | 1 | 0.009 | 15.259 us | 25.556 us | 25.556 us |
| SensitivityEarly100u | 198 | 137 | 137 | 61 | 1 | 0.009 | 15.259 us | 25.556 us | 25.556 us |
| SensitivityEarly20u | 198 | 99 | 99 | 99 | 1 | 0.000 | 17.861 us | 25.556 us | 25.556 us |
| SensitivityEarly50u | 198 | 99 | 99 | 99 | 1 | 0.000 | 17.861 us | 25.556 us | 25.556 us |
| SensitivityLate100u | 198 | 137 | 137 | 61 | 1 | 0.009 | 15.259 us | 25.556 us | 25.556 us |
| SensitivityLate25u | 198 | 137 | 137 | 61 | 1 | 0.009 | 15.259 us | 25.556 us | 25.556 us |
| SensitivityLate50u | 198 | 137 | 137 | 61 | 1 | 0.009 | 15.259 us | 25.556 us | 25.556 us |
| SensitivityQueue100u | 198 | 127 | 127 | 71 | 1 | 0.009 | 14.449 us | 16.996 us | 16.996 us |
| SensitivityQueue250u | 198 | 127 | 127 | 71 | 1 | 0.009 | 14.449 us | 16.996 us | 16.996 us |
| SensitivityQueue50u | 198 | 89 | 89 | 109 | 1 | 0.000 | 16.996 us | 16.996 us | 16.996 us |
| SensitivityTas100u | 198 | 137 | 137 | 61 | 1 | 0.009 | 15.259 us | 25.556 us | 25.556 us |
| SensitivityTas200u | 198 | 137 | 137 | 61 | 1 | 0.009 | 15.259 us | 25.556 us | 25.556 us |
| SensitivityTas50u | 198 | 137 | 137 | 61 | 1 | 0.009 | 15.259 us | 25.556 us | 25.556 us |

## 丢弃分解

| 配置 | 源端准入丢弃 | 网络丢弃 | Gate 丢弃 | Filter 丢弃 | Flow Meter 丢弃 | 早到丢弃 | Deadline 丢弃 |
|---|---:|---:|---:|---:|---:|---:|---:|
| SensitivityBurst1 | 71 | 0 | 0 | 0 | 10 | 0 | 61 |
| SensitivityBurst2 | 61 | 0 | 0 | 0 | 0 | 0 | 61 |
| SensitivityBurst4 | 61 | 0 | 0 | 0 | 0 | 0 | 61 |
| SensitivityDeadline1m | 61 | 0 | 0 | 0 | 0 | 0 | 61 |
| SensitivityDeadline2m | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| SensitivityDeadline500u | 61 | 0 | 0 | 0 | 0 | 0 | 61 |
| SensitivityEarly100u | 61 | 0 | 0 | 0 | 0 | 0 | 61 |
| SensitivityEarly20u | 99 | 0 | 0 | 0 | 0 | 38 | 61 |
| SensitivityEarly50u | 99 | 0 | 0 | 0 | 0 | 38 | 61 |
| SensitivityLate100u | 61 | 0 | 0 | 0 | 0 | 0 | 61 |
| SensitivityLate25u | 61 | 0 | 0 | 0 | 0 | 0 | 61 |
| SensitivityLate50u | 61 | 0 | 0 | 0 | 0 | 0 | 61 |
| SensitivityQueue100u | 71 | 0 | 0 | 0 | 0 | 0 | 71 |
| SensitivityQueue250u | 71 | 0 | 0 | 0 | 0 | 0 | 71 |
| SensitivityQueue50u | 109 | 0 | 0 | 0 | 0 | 0 | 109 |
| SensitivityTas100u | 61 | 0 | 0 | 0 | 0 | 0 | 61 |
| SensitivityTas200u | 61 | 0 | 0 | 0 | 0 | 0 | 61 |
| SensitivityTas50u | 61 | 0 | 0 | 0 | 0 | 0 | 61 |
