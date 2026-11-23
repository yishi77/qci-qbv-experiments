# OMNeT++ 三方案实验结果

本轮三套配置统一使用 mixed 扰动，周期 1 ms，Qbv ST 窗口为每周期最后 100 us，链路速率为 1 Gbit/s。

| 方案 | 输入缺失 | 源端发送 | 交付 | 丢弃 | 最大队列 | 平均时延 | 最大时延 | P99 | Deadline Miss |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qbv-only | 12 | 198 | 198 | 0 | 1 | 321.254 us | 1008.482 us | 1008.482 us | 61 |
| Full-Qci+Qbv | 12 | 198 | 99 | 99 | 1 | 17.861 us | 25.556 us | 25.556 us | 0 |
| Clipped-Qci+Qbv | 12 | 127 | 127 | 0 | 1 | 14.449 us | 16.996 us | 16.996 us | 0 |

## 入口统计

- Full-Qci+Qbv 的 Stream Gate 丢弃数从 INET 的 gateFilter 统计中读取。
- Clipped-Qci+Qbv 的入口丢弃数由自定义 TimingAdmissionUdpSourceApp 记录，该模块位于 ST 发送端应用边界，用于模拟裁剪后的入口准入逻辑。
- Qbv-only 保留所有生成帧，插帧和晚到帧由 Qbv 队列继续处理。

## 运行说明

三套仿真均在 Ubuntu 虚拟机中的 OMNeT++ 6.4.0 和 INET 4.7.0 上以 Cmdenv 成功结束。
当前结果用于验证三种方案的网络级接线和入口行为，后续可以加入更多 ST 流、更多交换机、同步误差和参数扫描。
