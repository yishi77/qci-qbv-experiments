#include <algorithm>
#include <cmath>
#include <map>
#include <string>
#include <vector>

#include "inet/applications/base/ApplicationPacket_m.h"
#include "inet/applications/udpapp/UdpBasicApp.h"
#include "inet/common/ModuleAccess.h"
#include "inet/common/Simsignals.h"
#include "inet/common/TimeTag_m.h"
#include "inet/common/packet/Packet.h"
#include "inet/networklayer/common/FragmentationTag_m.h"
#include "inet/networklayer/common/L3AddressResolver.h"

namespace inet {

class TimingAdmissionUdpSourceApp : public UdpBasicApp
{
  protected:
    enum FrameKind {
        ON_TIME,
        EARLY,
        LATE,
        LATE_BURST,
        INSERT
    };

    struct FramePlan {
        int sequence;
        simtime_t expected;
        simtime_t arrival;
        FrameKind kind;
    };

    std::string scenario;
    std::string admissionMode;
    std::string ablationMode;
    std::string dropPolicy;
    simtime_t cycle;
    simtime_t windowStart;
    simtime_t earlyOffset;
    simtime_t lateOffset;
    simtime_t burstOffset;
    simtime_t earlyTolerance;
    simtime_t lateTolerance;
    simtime_t deadline;
    simtime_t serviceTime;
    simtime_t maxQueueDelay;
    bool applyEarlyTolerance;
    int flowBurstFrames;
    int numFrames;
    int extraInsertCount;
    int planIndex = 0;
    int inputMissing = 0;
    int admissionDropped = 0;
    int filterDropped = 0;
    int flowDropped = 0;
    int earlyDropped = 0;
    int deadlineDropped = 0;
    int baseFramesSent = 0;
    int insertFramesSent = 0;
    std::vector<FramePlan> plans;
    std::map<long long, int> acceptedPerCycle;

    virtual void initialize(int stage) override;
    virtual void processStart() override;
    virtual void processSend() override;
    virtual void finish() override;

    FrameKind getBaseKind(int sequence) const;
    bool isDroppedInput(int sequence) const;
    simtime_t getExpectedTime(int sequence) const;
    simtime_t getBaseArrivalTime(int sequence) const;
    void buildPlans();
    bool admit(const FramePlan& plan);
    void sendPlannedPacket(const FramePlan& plan);
};

Define_Module(TimingAdmissionUdpSourceApp);

void TimingAdmissionUdpSourceApp::initialize(int stage)
{
    UdpBasicApp::initialize(stage);
    if (stage == INITSTAGE_LOCAL) {
        scenario = par("scenario").stdstringValue();
        admissionMode = par("admissionMode").stdstringValue();
        ablationMode = par("ablationMode").stdstringValue();
        dropPolicy = par("dropPolicy").stdstringValue();
        cycle = par("cycle");
        windowStart = par("windowStart");
        earlyOffset = par("earlyOffset");
        lateOffset = par("lateOffset");
        burstOffset = par("burstOffset");
        earlyTolerance = par("earlyTolerance");
        lateTolerance = par("lateTolerance");
        deadline = par("deadline");
        serviceTime = par("serviceTime");
        maxQueueDelay = par("maxQueueDelay");
        applyEarlyTolerance = par("applyEarlyTolerance");
        flowBurstFrames = par("flowBurstFrames");
        numFrames = par("numFrames");
        extraInsertCount = par("extraInsertCount");
        buildPlans();
    }
}

TimingAdmissionUdpSourceApp::FrameKind TimingAdmissionUdpSourceApp::getBaseKind(int sequence) const
{
    bool mixed = scenario == "mixed";
    if ((scenario == "early" || mixed) && (sequence % 10 == 2 || sequence % 10 == 3))
        return EARLY;
    if ((scenario == "late" || mixed) && (sequence % 10 == 5 || sequence % 10 == 6 || sequence % 10 == 7))
        return LATE;
    if ((scenario == "burst" || mixed) && sequence % 25 == 10)
        return LATE_BURST;
    return ON_TIME;
}

bool TimingAdmissionUdpSourceApp::isDroppedInput(int sequence) const
{
    return (scenario == "drop" || scenario == "mixed") && sequence % 17 == 4;
}

simtime_t TimingAdmissionUdpSourceApp::getExpectedTime(int sequence) const
{
    return windowStart + sequence * cycle;
}

simtime_t TimingAdmissionUdpSourceApp::getBaseArrivalTime(int sequence) const
{
    simtime_t expected = getExpectedTime(sequence);
    switch (getBaseKind(sequence)) {
        case EARLY: return expected - earlyOffset;
        case LATE: return expected + lateOffset;
        case LATE_BURST: return expected + burstOffset;
        default: return expected;
    }
}

void TimingAdmissionUdpSourceApp::buildPlans()
{
    plans.clear();
    for (int sequence = 0; sequence < numFrames; sequence++) {
        if (isDroppedInput(sequence)) {
            inputMissing++;
            continue;
        }

        FramePlan base{sequence, getExpectedTime(sequence), getBaseArrivalTime(sequence), getBaseKind(sequence)};
        plans.push_back(base);

        int insertCount = extraInsertCount;
        if ((scenario == "insert" || scenario == "mixed") && sequence % 20 == 8)
            insertCount++;
        for (int insertIndex = 0; insertIndex < insertCount; insertIndex++) {
            FramePlan inserted{sequence, base.expected, base.arrival + SimTime(insertIndex + 1, SIMTIME_US), INSERT};
            plans.push_back(inserted);
        }
    }

    std::sort(plans.begin(), plans.end(), [](const FramePlan& left, const FramePlan& right) {
        if (left.arrival != right.arrival)
            return left.arrival < right.arrival;
        if (left.sequence != right.sequence)
            return left.sequence < right.sequence;
        return left.kind < right.kind;
    });
}

void TimingAdmissionUdpSourceApp::processStart()
{
    socket.setOutputGate(gate("socketOut"));
    const char *localAddress = par("localAddress");
    socket.bind(*localAddress ? L3AddressResolver().resolve(localAddress) : L3Address(), localPort);
    setSocketOptions();

    const char *destAddrs = par("destAddresses");
    cStringTokenizer tokenizer(destAddrs);
    const char *token;
    while ((token = tokenizer.nextToken()) != nullptr) {
        destAddressStr.push_back(token);
        L3Address result;
        L3AddressResolver().tryResolve(token, result);
        if (result.isUnspecified())
            EV_ERROR << "cannot resolve destination address: " << token << endl;
        destAddresses.push_back(result);
    }

    if (!plans.empty()) {
        selfMsg->setKind(SEND);
        scheduleAt(plans.front().arrival, selfMsg);
    }
    else {
        selfMsg->setKind(STOP);
        scheduleAt(simTime(), selfMsg);
    }
}

bool TimingAdmissionUdpSourceApp::admit(const FramePlan& plan)
{
    bool useTimestamp = false;
    bool useSequence = false;
    bool useFlowMeter = false;

    if (admissionMode == "clipped") {
        useTimestamp = true;
        useSequence = true;
    }
    else if (admissionMode == "ablation") {
        useTimestamp = ablationMode == "timestamp" || ablationMode == "timestamp_seq" || ablationMode == "timestamp_flow" || ablationMode == "proposed";
        useSequence = ablationMode == "timestamp_seq" || ablationMode == "proposed";
        useFlowMeter = ablationMode == "flow" || ablationMode == "timestamp_flow" || ablationMode == "proposed";
    }
    else if (admissionMode == "policy") {
        useTimestamp = dropPolicy != "none";
    }

    long long cycleIndex = static_cast<long long>(std::floor(plan.expected / cycle));

    if (useSequence && plan.kind == INSERT) {
        filterDropped++;
        return false;
    }

    if (useFlowMeter && acceptedPerCycle[cycleIndex] >= flowBurstFrames) {
        flowDropped++;
        return false;
    }

    if (!useTimestamp) {
        if (useFlowMeter)
            acceptedPerCycle[cycleIndex]++;
        return true;
    }

    simtime_t currentWindow = cycleIndex * cycle + windowStart;
    if (currentWindow < plan.arrival)
        currentWindow += cycle;
    simtime_t predictedWait = currentWindow - plan.arrival;
    simtime_t predictedFinish = currentWindow + serviceTime;

    if (applyEarlyTolerance && plan.arrival < plan.expected - earlyTolerance) {
        earlyDropped++;
        return false;
    }

    if (admissionMode == "policy" && dropPolicy == "deadline_queue" && predictedWait > maxQueueDelay) {
        deadlineDropped++;
        return false;
    }

    bool late = plan.arrival > plan.expected + lateTolerance;
    if (late && predictedFinish > plan.expected + deadline) {
        deadlineDropped++;
        return false;
    }

    if (useFlowMeter)
        acceptedPerCycle[cycleIndex]++;
    return true;
}

void TimingAdmissionUdpSourceApp::sendPlannedPacket(const FramePlan& plan)
{
    std::string packetLabel = std::string(this->packetName ? this->packetName : "ST") + "-" + std::to_string(plan.sequence);
    if (plan.kind == INSERT)
        packetLabel += "-insert";

    auto packet = new Packet(packetLabel.c_str());
    if (dontFragment)
        packet->addTag<FragmentationReq>()->setDontFragment(true);

    const auto& payload = makeShared<ApplicationPacket>();
    payload->setChunkLength(B(par("messageLength")));
    payload->setSequenceNumber(plan.sequence);
    payload->addTag<CreationTimeTag>()->setCreationTime(plan.expected);
    packet->addTag<CreationTimeTag>()->setCreationTime(plan.expected);
    packet->insertAtBack(payload);

    emit(packetSentSignal, packet);
    socket.sendTo(packet, chooseDestAddr(), destPort);
    numSent++;
    if (plan.kind == INSERT)
        insertFramesSent++;
    else
        baseFramesSent++;
}

void TimingAdmissionUdpSourceApp::processSend()
{
    if (planIndex >= static_cast<int>(plans.size())) {
        selfMsg->setKind(STOP);
        scheduleAt(simTime(), selfMsg);
        return;
    }

    const FramePlan& plan = plans[planIndex++];
    if (admit(plan))
        sendPlannedPacket(plan);
    else
        admissionDropped++;

    if (planIndex < static_cast<int>(plans.size())) {
        selfMsg->setKind(SEND);
        scheduleAt(plans[planIndex].arrival, selfMsg);
    }
    else {
        selfMsg->setKind(STOP);
        scheduleAt(simTime(), selfMsg);
    }
}

void TimingAdmissionUdpSourceApp::finish()
{
    recordScalar("planned base frames", numFrames);
    recordScalar("missing input frames", inputMissing);
    recordScalar("admission dropped frames", admissionDropped);
    recordScalar("filter dropped frames", filterDropped);
    recordScalar("flow dropped frames", flowDropped);
    recordScalar("early dropped frames", earlyDropped);
    recordScalar("deadline dropped frames", deadlineDropped);
    recordScalar("base frames sent", baseFramesSent);
    recordScalar("insert frames sent", insertFramesSent);
    UdpBasicApp::finish();
}

} // namespace inet
