from pathlib import Path

base = Path(__file__).resolve().parents[1] / "configs"
text = (base / "omnetpp.ini").read_text(encoding="utf-8")
text = text.replace(
    "network = qci_qbv.QciQbvThreeSchemes",
    "network = qci_qbv.QciQbvMultiSwitch",
)
text = text.replace("sim-time-limit = 300ms", "sim-time-limit = 300ms\nresult-dir = results_multiswitch")
text = text.replace("*.switch", "*.switch*")
text = text.replace('{vlan: 4, stream: "st"}', '{pcp: 4, stream: "st"}')
insert = """
# Multi-switch stream forwarding and decoding
*.switch*.hasIncomingStreams = true
*.switch*.hasOutgoingStreams = true
*.switch*.bridging.streamCoder.decoder.mapping = [{pcp: 0, stream: "nst"}, {pcp: 4, stream: "st"}]
*.switch*.bridging.streamCoder.encoder.mapping = [{stream: "nst", pcp: 0}, {stream: "st", pcp: 4}]
*.switch*.bridging.directionReverser.reverser.excludeEncapsulationProtocols = ["ieee8021qctag"]
*.server.hasIncomingStreams = true
*.server.bridging.streamCoder.decoder.mapping = [{pcp: 0, stream: "nst"}, {pcp: 4, stream: "st"}]

"""
text = text.replace("[Config QbvOnly]", insert + "[Config QbvOnly]")
(base / "omnetpp_multiswitch.ini").write_text(text, encoding="utf-8")
