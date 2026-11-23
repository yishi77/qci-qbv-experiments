# 实验四至六运行说明

实验四使用 `omnetpp_ablation.ini`，结果写入 `results_ablation`。

实验五使用 `omnetpp_drop_policy.ini`，结果写入 `results_drop_policy`。

实验六使用 `omnetpp_sensitivity.ini`，结果写入 `results_sensitivity`。

三组结果目录彼此独立。每个配置均生成 `.sca`、`.vec` 和 `.vci` 文件。结果汇总分别位于 `three_scheme_ablation_results.csv/.md`、`three_scheme_drop_policy_results.csv/.md` 和 `three_scheme_sensitivity_results.csv/.md`。

虚拟机中的运行环境为 OMNeT++ 6.4.0、INET 4.7.0 和 QciQbv 自定义模块。运行时使用清理后的 NED 路径，避免工程内重复 INET 源码造成类型重复。
