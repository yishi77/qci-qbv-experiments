# Qci/Qbv 时间扰动实验

这个仓库保存 Qbv-only、Full-Qci+Qbv 和 Clipped-Qci+Qbv 三种机制的 OMNeT++ 实验源码、配置和汇总结果。

实验围绕周期性 ST 流的早到、晚到、丢帧、插帧和过载积压展开。实现使用 OMNeT++ 6.4.0、INET 4.7.0 和 C++ 自定义应用模块。

## 实验内容

- 基础实验使用 `configs/omnetpp.ini`。
- 帧积压压力实验使用 `configs/omnetpp_backlog.ini`。
- 三交换机实验使用 `configs/omnetpp_multiswitch.ini`。
- 实验四消融比较使用 `configs/omnetpp_ablation.ini`。
- 实验五丢弃策略比较使用 `configs/omnetpp_drop_policy.ini`。
- 实验六参数敏感性扫描使用 `configs/omnetpp_sensitivity.ini`。
- 实验七交换机入口下沉版 Clipped-Qci（含 `ReorderTimeout` 与早到暂存）使用 `configs/omnetpp_exp7.ini`。

实验四比较 Flow Meter、时间判断、序号判断和完整 Proposed 组合。实验五比较不主动丢弃、Deadline 丢弃和 Deadline 加 MaxQueueDelay 丢弃。实验六扫描时间容差、截止时间、排队时延、突发阈值和 TAS 窗口长度。

## 目录结构

```text
src/       C++ 自定义源端和接收端应用
ned/       自定义 NED 类型和网络拓扑
configs/   OMNeT++ ini 配置
scripts/   配置生成、结果解析和综合报告脚本
docs/      实验四至六分析和运行说明
results/   CSV 和 Markdown 汇总结果
Makefile   自定义模块构建文件
```

原始 `.sca`、`.vec` 和 `.vci` 文件没有提交到仓库。它们可以由下面的命令重新生成，且单轮结果可能占用数百 MB。构建产物 `libQciQbv.so`、目标文件和 `out/` 目录同样不提交。

## 环境要求

- Linux，推荐 Ubuntu 虚拟机
- OMNeT++ 6.4.0
- INET 4.7.0
- GCC 15 或兼容的 C++17 编译器
- GNU Make
- Python 3.10 或更高版本

先准备 OMNeT++ 和 INET，并确认 INET 已经构建出 `libINET.so`。仓库的 Makefile 保留了当前虚拟机路径作为默认值，也支持通过环境变量覆盖。

```bash
export OMNETPP_ROOT=/home/yishi/workspace/omnet++/omnetpp-6.4.0
export INET_ROOT=/home/yishi/workspace/inet-4.7.0
```

## 构建自定义模块

在仓库根目录执行。

```bash
make clean
make OMNETPP_ROOT="$OMNETPP_ROOT" INET_ROOT="$INET_ROOT"
```

成功后会生成 `libQciQbv.so`。源码依赖 INET 的头文件和动态库，仓库不复制 INET 源码。

## 手动运行一个配置

运行时需要把仓库的 `ned/` 和 INET 的 NED 目录加入 NED 搜索路径。

```bash
OPPRUN="$OMNETPP_ROOT/bin/opp_run"
NED_PATH="$PWD/ned:$INET_ROOT/src"

"$OPPRUN" -u Cmdenv \
  -n "$NED_PATH" \
  -l "$INET_ROOT/out/gcc-release/src/libINET.so" \
  -l "$PWD/libQciQbv.so" \
  -c QbvOnly \
  --network=qci_qbv.QciQbvThreeSchemes \
  configs/omnetpp.ini
```

结果会根据配置中的 `result-dir` 写入仓库根目录下的独立目录，例如 `results_baseline`。

## 复现全部六类实验

下面的命令逐个运行配置。每个配置都使用固定的配置名和独立的 `result-dir`。

```bash
run() {
  "$OPPRUN" -u Cmdenv -n "$NED_PATH" \
    -l "$INET_ROOT/out/gcc-release/src/libINET.so" \
    -l "$PWD/libQciQbv.so" \
    -c "$1" --network="$2" "$3"
}

run QbvOnly qci_qbv.QciQbvThreeSchemes configs/omnetpp.ini
run FullQciQbv qci_qbv.QciQbvThreeSchemes configs/omnetpp.ini
run ClippedQciQbv qci_qbv.QciQbvThreeSchemes configs/omnetpp.ini

run BacklogQbvOnly qci_qbv.QciQbvThreeSchemes configs/omnetpp_backlog.ini
run BacklogFullQciQbv qci_qbv.QciQbvThreeSchemes configs/omnetpp_backlog.ini
run BacklogClippedQciQbv qci_qbv.QciQbvThreeSchemes configs/omnetpp_backlog.ini

run QbvOnly qci_qbv.QciQbvMultiSwitch configs/omnetpp_multiswitch.ini
run FullQciQbv qci_qbv.QciQbvMultiSwitch configs/omnetpp_multiswitch.ini
run ClippedQciQbv qci_qbv.QciQbvMultiSwitch configs/omnetpp_multiswitch.ini

for c in AblationFlowMeterOnly AblationTimestampOnly AblationTimestampSequence AblationTimestampFlow AblationProposed; do
  run "$c" qci_qbv.QciQbvThreeSchemes configs/omnetpp_ablation.ini
done

for c in DropNoProactive DropDeadline DropDeadlineQueue; do
  run "$c" qci_qbv.QciQbvThreeSchemes configs/omnetpp_drop_policy.ini
done

for c in \
  SensitivityEarly20u SensitivityEarly50u SensitivityEarly100u \
  SensitivityLate25u SensitivityLate50u SensitivityLate100u \
  SensitivityDeadline500u SensitivityDeadline1m SensitivityDeadline2m \
  SensitivityQueue50u SensitivityQueue100u SensitivityQueue250u \
  SensitivityBurst1 SensitivityBurst2 SensitivityBurst4 \
  SensitivityTas50u SensitivityTas100u SensitivityTas200u; do
  run "$c" qci_qbv.QciQbvThreeSchemes configs/omnetpp_sensitivity.ini
done
```

实验四、五、六的结果目录分别为 `results_ablation`、`results_drop_policy` 和 `results_sensitivity`。基础、压力和多交换机结果目录分别为 `results_baseline`、`results_backlog` 和 `results_multiswitch`。

## 重新生成配置和汇总报告

配置生成脚本和结果解析脚本使用仓库相对路径，可以在仓库根目录执行。

```bash
python3 scripts/create_multiswitch_config.py
python3 scripts/create_exp456_configs.py

python3 scripts/parse_omnet_results.py
python3 scripts/parse_backlog_results.py
python3 scripts/parse_multiswitch_results.py
python3 scripts/parse_exp456_results.py
python3 scripts/compile_three_round_report.py
```

脚本会读取各个 `results_*` 目录中的 OMNeT++ 标量和向量结果，并重新生成 `results/` 中的 CSV 和 Markdown 汇总文件。若要保留可重复的原始结果，应在运行后把生成的 `results_*` 目录单独归档。

## 结果解读

仅使用 Qbv 时，过载帧会继续进入出口队列，容易造成队列积压和尾部时延增长。Flow Meter 可以限制突发，但不能单独判断晚到帧。时间判断负责识别时效，序号判断负责过滤插入帧和重复帧，Deadline 与 MaxQueueDelay 用于主动清除已经失去业务价值的帧。

当前推荐后续多流压力实验从下面的参数开始。

```text
EarlyTolerance = 100us
LateTolerance = 50us
Deadline = 1ms
MaxQueueDelay = 100us
FlowBurstFrames = 2
```

## 当前实现边界

`ReorderTimeout` 尚未接入当前应用模块。时间准入模块当前位于发送端应用边界，尚未下沉为交换机入口模块。多交换机实验尚未加入每跳时钟偏差、传播时延和多随机种子重复。实验结果用于机制验证和参数初筛，后续研究需要补齐这些因素。

