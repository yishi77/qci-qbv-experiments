from pathlib import Path

root = Path(__file__).resolve().parents[1] / "configs"
original = (root / "omnetpp.ini").read_text(encoding="utf-8")
common = original.split("[Config QbvOnly]", 1)[0]

def make_file(name: str, result_dir: str, sections: list[str], extra: str = ""):
    text = common.replace("result-dir = results_baseline", f"result-dir = {result_dir}")
    text += "\n" + extra + "\n" + "\n".join(sections)
    (root / name).write_text(text, encoding="utf-8")


ablation_sections = []
for config, mode in [
    ("AblationFlowMeterOnly", "flow"),
    ("AblationTimestampOnly", "timestamp"),
    ("AblationTimestampSequence", "timestamp_seq"),
    ("AblationTimestampFlow", "timestamp_flow"),
    ("AblationProposed", "proposed"),
]:
    ablation_sections.append(f"""[Config {config}]
description = "Experiment 4 ablation: {mode}"
*.stClient.app[0].scenario = "mixed"
*.stClient.app[0].admissionMode = "ablation"
*.stClient.app[0].ablationMode = "{mode}"
*.stClient.app[0].dropPolicy = "none"
*.stClient.app[0].applyEarlyTolerance = false
*.stClient.app[0].flowBurstFrames = 1
*.switch.hasIngressTrafficFiltering = false
""")
make_file("omnetpp_ablation.ini", "results_ablation", ablation_sections)


drop_sections = []
for config, policy, max_delay in [
    ("DropNoProactive", "none", "1ms"),
    ("DropDeadline", "deadline", "1ms"),
    ("DropDeadlineQueue", "deadline_queue", "100us"),
]:
    drop_sections.append(f"""[Config {config}]
description = "Experiment 5 discard policy: {policy}"
*.stClient.app[0].scenario = "mixed"
*.stClient.app[0].admissionMode = "policy"
*.stClient.app[0].dropPolicy = "{policy}"
*.stClient.app[0].maxQueueDelay = {max_delay}
*.stClient.app[0].applyEarlyTolerance = false
*.stClient.app[0].flowBurstFrames = 1
*.switch.hasIngressTrafficFiltering = false
""")
make_file("omnetpp_drop_policy.ini", "results_drop_policy", drop_sections)


sensitivity_sections = []
for value in ["20us", "50us", "100us"]:
    sensitivity_sections.append(f"""[Config SensitivityEarly{value.replace('us', 'u')}]
description = "Experiment 6 EarlyTolerance {value}"
*.stClient.app[0].scenario = "mixed"
*.stClient.app[0].admissionMode = "policy"
*.stClient.app[0].dropPolicy = "deadline_queue"
*.stClient.app[0].earlyTolerance = {value}
*.stClient.app[0].maxQueueDelay = 1ms
*.stClient.app[0].applyEarlyTolerance = true
*.switch.hasIngressTrafficFiltering = false
""")
for value in ["25us", "50us", "100us"]:
    sensitivity_sections.append(f"""[Config SensitivityLate{value.replace('us', 'u')}]
description = "Experiment 6 LateTolerance {value}"
*.stClient.app[0].scenario = "mixed"
*.stClient.app[0].admissionMode = "policy"
*.stClient.app[0].dropPolicy = "deadline_queue"
*.stClient.app[0].lateTolerance = {value}
*.stClient.app[0].maxQueueDelay = 1ms
*.stClient.app[0].applyEarlyTolerance = false
*.switch.hasIngressTrafficFiltering = false
""")
for value in ["500us", "1ms", "2ms"]:
    sensitivity_sections.append(f"""[Config SensitivityDeadline{value.replace('us', 'u').replace('ms', 'm')}]
description = "Experiment 6 Deadline {value}"
*.stClient.app[0].scenario = "mixed"
*.stClient.app[0].admissionMode = "policy"
*.stClient.app[0].dropPolicy = "deadline_queue"
*.stClient.app[0].deadline = {value}
*.stClient.app[0].maxQueueDelay = 1ms
*.stClient.app[0].applyEarlyTolerance = false
*.switch.hasIngressTrafficFiltering = false
""")
for value in ["50us", "100us", "250us"]:
    sensitivity_sections.append(f"""[Config SensitivityQueue{value.replace('us', 'u')}]
description = "Experiment 6 MaxQueueDelay {value}"
*.stClient.app[0].scenario = "mixed"
*.stClient.app[0].admissionMode = "policy"
*.stClient.app[0].dropPolicy = "deadline_queue"
*.stClient.app[0].maxQueueDelay = {value}
*.stClient.app[0].applyEarlyTolerance = false
*.switch.hasIngressTrafficFiltering = false
""")
for value in ["1", "2", "4"]:
    sensitivity_sections.append(f"""[Config SensitivityBurst{value}]
description = "Experiment 6 FlowMeter burst frames {value}"
*.stClient.app[0].scenario = "mixed"
*.stClient.app[0].admissionMode = "ablation"
*.stClient.app[0].ablationMode = "timestamp_flow"
*.stClient.app[0].flowBurstFrames = {value}
*.stClient.app[0].applyEarlyTolerance = false
*.switch.hasIngressTrafficFiltering = false
""")
for window, start in [("50us", "950us"), ("100us", "900us"), ("200us", "800us")]:
    sensitivity_sections.append(f"""[Config SensitivityTas{window.replace('us', 'u')}]
description = "Experiment 6 TAS ST window {window}"
*.stClient.app[0].scenario = "mixed"
*.stClient.app[0].admissionMode = "policy"
*.stClient.app[0].dropPolicy = "deadline_queue"
*.stClient.app[0].windowStart = {start}
*.stClient.app[0].maxQueueDelay = 1ms
*.stClient.app[0].applyEarlyTolerance = false
*.server.app[1].windowStart = {start}
*.switch.eth[*].macLayer.queue.transmissionGate[0].durations = [{start}, {window}]
*.switch.eth[*].macLayer.queue.transmissionGate[1].durations = [{start}, {window}]
*.switch.hasIngressTrafficFiltering = false
""")
make_file("omnetpp_sensitivity.ini", "results_sensitivity", sensitivity_sections)
