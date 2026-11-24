#include <cmath>
#include <map>
#include <string>

#include "inet/applications/base/ApplicationPacket_m.h"
#include "inet/common/TimeTag_m.h"
#include "inet/common/packet/Packet.h"
#include "inet/common/packet/chunk/BytesChunk.h"
#include "inet/queueing/base/PacketFilterBase.h"
#include "QciSequenceTag.h"

namespace inet {

class ClippedQciIngressFilter : public queueing::PacketFilterBase
{
  protected:
    enum class Decision {
        PASS,
        HOLD,
        DROP_INVALID,
        DROP_EARLY,
        DROP_FLOW,
        DROP_DEADLINE,
        DROP_DUPLICATE
    };

    simtime_t cycle;
    simtime_t windowStart;
    simtime_t windowDuration;
    simtime_t earlyTolerance;
    simtime_t lateTolerance;
    simtime_t deadline;
    simtime_t maxQueueDelay;
    simtime_t serviceTime;
    simtime_t reorderTimeout;
    int maxReorderBuffer;
    int flowBurstFrames;
    int expectedSequence;
    b payloadLength;
    bool useFlowMeter = true;
    bool applyEarlyTolerance = true;
    bool useMaxQueueDelay = true;
    simtime_t gapDeadline = SIMTIME_ZERO;

    cMessage *releaseTimer = nullptr;
    std::map<int, Packet *> pendingPackets;
    std::map<int, simtime_t> pendingReleaseTimes;
    std::map<long long, int> acceptedPerCycle;

    int passedPackets = 0;
    int bufferedPackets = 0;
    int releasedAfterReorder = 0;
    int droppedInvalid = 0;
    int droppedEarly = 0;
    int droppedFlow = 0;
    int droppedDeadline = 0;
    int droppedDuplicate = 0;
    int droppedGapTimeout = 0;
    int droppedBuffer = 0;

    virtual void initialize(int stage) override;
    virtual void handleMessage(cMessage *message) override;
    virtual void pushPacket(Packet *packet, const cGate *gate) override;
    virtual bool matchesPacket(const Packet *packet) const override { return true; }
    virtual void finish() override;

    int getSequence(const Packet *packet) const;
    simtime_t getExpectedTime(const Packet *packet, int sequence) const;
    long long getCycleIndex(simtime_t expected) const;
    Decision evaluate(Packet *packet) const;
    void acceptPacket(Packet *packet);
    void holdPacket(Packet *packet, simtime_t releaseTime);
    void dropPacketWithDecision(Packet *packet, Decision decision);
    void processPacket(Packet *packet);
    void flushReadyPackets();
    void releaseDuePackets();
    void scheduleReleaseTimer();
    void skipMissingSequence();

  public:
    virtual ~ClippedQciIngressFilter();
};

Define_Module(ClippedQciIngressFilter);

void ClippedQciIngressFilter::initialize(int stage)
{
    queueing::PacketFilterBase::initialize(stage);
    if (stage == INITSTAGE_LOCAL) {
        cycle = par("cycle");
        windowStart = par("windowStart");
        windowDuration = par("windowDuration");
        earlyTolerance = par("earlyTolerance");
        lateTolerance = par("lateTolerance");
        deadline = par("deadline");
        maxQueueDelay = par("maxQueueDelay");
        serviceTime = par("serviceTime");
        reorderTimeout = par("reorderTimeout");
        maxReorderBuffer = par("maxReorderBuffer");
        flowBurstFrames = par("flowBurstFrames");
        expectedSequence = par("initialSequence");
        payloadLength = b(par("payloadLength"));
        useFlowMeter = par("useFlowMeter");
        applyEarlyTolerance = par("applyEarlyTolerance");
        useMaxQueueDelay = par("useMaxQueueDelay");
        releaseTimer = new cMessage("clippedQciReleaseTimer");
    }
}

ClippedQciIngressFilter::~ClippedQciIngressFilter()
{
    for (auto& entry : pendingPackets)
        delete entry.second;
    cancelAndDelete(releaseTimer);
}

void ClippedQciIngressFilter::handleMessage(cMessage *message)
{
    if (message == releaseTimer) {
        releaseDuePackets();
        return;
    }

    auto packet = check_and_cast<Packet *>(message);
    pushPacket(packet, packet->getArrivalGate());
}

int ClippedQciIngressFilter::getSequence(const Packet *packet) const
{
    auto sequenceTag = packet->findTag<QciSequenceTag>();
    if (sequenceTag != nullptr) {
        return sequenceTag->getSequenceNumber();
    }
    auto markerChunk = packet->peekAtBack<BytesChunk>(B(8), Chunk::PF_ALLOW_INCOMPLETE | Chunk::PF_ALLOW_INCORRECT | Chunk::PF_ALLOW_IMPROPERLY_REPRESENTED);
    if (markerChunk != nullptr && markerChunk->getBytes().size() >= 8) {
        const auto& bytes = markerChunk->getBytes();
        if (bytes[0] == 'Q' && bytes[1] == 'C' && bytes[2] == 'I' && bytes[3] == '1') {
            return (bytes[4] << 24) | (bytes[5] << 16) | (bytes[6] << 8) | bytes[7];
        }
    }
    b applicationOffset = packet->getDataLength() - payloadLength - B(8);
    auto applicationPacket = applicationOffset >= b(0) ? packet->peekDataAt<ApplicationPacket>(applicationOffset, payloadLength, Chunk::PF_ALLOW_INCOMPLETE | Chunk::PF_ALLOW_INCORRECT | Chunk::PF_ALLOW_IMPROPERLY_REPRESENTED) : nullptr;
    if (applicationPacket != nullptr) {
        return applicationPacket->getSequenceNumber();
    }
    std::string name(packet->getName());
    std::size_t end = name.find("-insert");
    if (end == std::string::npos)
        end = name.size();
    std::size_t separator = name.rfind('-', end == 0 ? 0 : end - 1);
    if (separator == std::string::npos || separator + 1 >= end)
        return -1;
    try {
        int parsed = std::stoi(name.substr(separator + 1, end - separator - 1));
        return parsed;
    }
    catch (...) {
        return -1;
    }
}

simtime_t ClippedQciIngressFilter::getExpectedTime(const Packet *packet, int sequence) const
{
    auto creationTimeTag = packet->findTag<CreationTimeTag>();
    if (creationTimeTag != nullptr)
        return creationTimeTag->getCreationTime();
    return windowStart + sequence * cycle;
}

long long ClippedQciIngressFilter::getCycleIndex(simtime_t expected) const
{
    return static_cast<long long>(std::floor((expected - windowStart) / cycle));
}

ClippedQciIngressFilter::Decision ClippedQciIngressFilter::evaluate(Packet *packet) const
{
    int sequence = getSequence(packet);
    if (sequence < 0)
        return Decision::DROP_INVALID;
    if (sequence < expectedSequence || pendingPackets.count(sequence))
        return Decision::DROP_DUPLICATE;

    simtime_t expected = getExpectedTime(packet, sequence);
    simtime_t now = simTime();
    if (applyEarlyTolerance && now < expected - earlyTolerance)
        return Decision::DROP_EARLY;
    if (now < expected)
        return Decision::HOLD;

    long long cycleIndex = getCycleIndex(expected);
    if (useFlowMeter && acceptedPerCycle.count(cycleIndex) && acceptedPerCycle.at(cycleIndex) >= flowBurstFrames)
        return Decision::DROP_FLOW;

    simtime_t windowOpen = expected;
    simtime_t windowClose = windowOpen + windowDuration;
    simtime_t predictedWait = SIMTIME_ZERO;
    simtime_t predictedFinish = SIMTIME_ZERO;

    if (now + serviceTime <= windowClose) {
        predictedWait = SIMTIME_ZERO;
        predictedFinish = now + serviceTime;
    }
    else {
        simtime_t nextWindow = windowOpen + cycle;
        while (nextWindow + windowDuration < now + serviceTime)
            nextWindow += cycle;
        if (now < nextWindow) {
            predictedWait = nextWindow - now;
            predictedFinish = nextWindow + serviceTime;
        }
        else {
            predictedWait = SIMTIME_ZERO;
            predictedFinish = now + serviceTime;
        }
    }

    if (useMaxQueueDelay && predictedWait > maxQueueDelay)
        return Decision::DROP_DEADLINE;

    bool late = now > expected + lateTolerance;
    if (late && predictedFinish > expected + deadline)
        return Decision::DROP_DEADLINE;

    return Decision::PASS;
}

void ClippedQciIngressFilter::dropPacketWithDecision(Packet *packet, Decision decision)
{
    switch (decision) {
        case Decision::DROP_INVALID: droppedInvalid++; break;
        case Decision::DROP_EARLY: droppedEarly++; break;
        case Decision::DROP_FLOW: droppedFlow++; break;
        case Decision::DROP_DEADLINE: droppedDeadline++; break;
        case Decision::DROP_DUPLICATE: droppedDuplicate++; break;
        default: break;
    }
    dropPacket(packet);
}

void ClippedQciIngressFilter::acceptPacket(Packet *packet)
{
    int sequence = getSequence(packet);
    long long cycleIndex = getCycleIndex(getExpectedTime(packet, sequence));
    acceptedPerCycle[cycleIndex]++;
    passedPackets++;
    emit(packetPushedOutSignal, packet);
    pushOrSendPacket(packet, outputGate, consumer);
    expectedSequence = sequence + 1;
}

void ClippedQciIngressFilter::holdPacket(Packet *packet, simtime_t releaseTime)
{
    int sequence = getSequence(packet);
    if (pendingPackets.size() >= static_cast<size_t>(maxReorderBuffer) || pendingPackets.count(sequence)) {
        droppedBuffer++;
        dropPacket(packet);
        return;
    }
    pendingPackets[sequence] = packet;
    pendingReleaseTimes[sequence] = releaseTime;
    bufferedPackets++;
    scheduleReleaseTimer();
}

void ClippedQciIngressFilter::processPacket(Packet *packet)
{
    int sequence = getSequence(packet);
    if (sequence < 0) {
        dropPacketWithDecision(packet, Decision::DROP_INVALID);
        return;
    }
    if (sequence < expectedSequence || pendingPackets.count(sequence)) {
        dropPacketWithDecision(packet, Decision::DROP_DUPLICATE);
        return;
    }

    if (sequence > expectedSequence) {
        if (gapDeadline == SIMTIME_ZERO)
            gapDeadline = simTime() + reorderTimeout;
        holdPacket(packet, gapDeadline);
        return;
    }

    Decision decision = evaluate(packet);
    if (decision == Decision::PASS) {
        acceptPacket(packet);
        flushReadyPackets();
    }
    else if (decision == Decision::HOLD) {
        holdPacket(packet, getExpectedTime(packet, sequence));
    }
    else {
        dropPacketWithDecision(packet, decision);
        if (decision != Decision::DROP_DUPLICATE)
            expectedSequence++;
        flushReadyPackets();
    }
}

void ClippedQciIngressFilter::pushPacket(Packet *packet, const cGate *gate)
{
    Enter_Method("pushPacket");
    take(packet);
    emit(packetPushedInSignal, packet);
    handlePacketProcessed(packet);
    processPacket(packet);
}

void ClippedQciIngressFilter::skipMissingSequence()
{
    if (pendingPackets.empty() || gapDeadline == SIMTIME_ZERO || simTime() < gapDeadline)
        return;
    int firstPending = pendingPackets.begin()->first;
    if (firstPending > expectedSequence) {
        droppedGapTimeout += firstPending - expectedSequence;
        expectedSequence = firstPending;
    }
    gapDeadline = SIMTIME_ZERO;
}

void ClippedQciIngressFilter::flushReadyPackets()
{
    if (!pendingPackets.empty() && pendingPackets.begin()->first == expectedSequence) {
        gapDeadline = SIMTIME_ZERO;
        pendingReleaseTimes[expectedSequence] = SIMTIME_ZERO;
    }
    skipMissingSequence();
    while (!pendingPackets.empty() && pendingPackets.begin()->first == expectedSequence) {
        int sequence = pendingPackets.begin()->first;
        Packet *packet = pendingPackets.begin()->second;
        simtime_t releaseTime = pendingReleaseTimes[sequence];
        pendingPackets.erase(pendingPackets.begin());
        pendingReleaseTimes.erase(sequence);
        if (releaseTime > simTime()) {
            pendingPackets[sequence] = packet;
            pendingReleaseTimes[sequence] = releaseTime;
            break;
        }

        Decision decision = evaluate(packet);
        if (decision == Decision::PASS) {
            releasedAfterReorder++;
            acceptPacket(packet);
        }
        else if (decision == Decision::HOLD) {
            pendingPackets[sequence] = packet;
            pendingReleaseTimes[sequence] = getExpectedTime(packet, sequence);
            break;
        }
        else {
            dropPacketWithDecision(packet, decision);
            expectedSequence++;
        }
    }
    scheduleReleaseTimer();
}

void ClippedQciIngressFilter::releaseDuePackets()
{
    skipMissingSequence();
    flushReadyPackets();
}

void ClippedQciIngressFilter::scheduleReleaseTimer()
{
    if (releaseTimer->isScheduled())
        cancelEvent(releaseTimer);
    if (pendingPackets.empty())
        return;

    simtime_t next = SIMTIME_MAX;
    if (gapDeadline != SIMTIME_ZERO)
        next = std::min(next, gapDeadline);
    for (const auto& entry : pendingReleaseTimes)
        next = std::min(next, entry.second);
    scheduleAt(std::max(simTime(), next), releaseTimer);
}

void ClippedQciIngressFilter::finish()
{
    recordScalar("passed packets", passedPackets);
    recordScalar("buffered packets", bufferedPackets);
    recordScalar("released after reorder", releasedAfterReorder);
    recordScalar("dropped invalid", droppedInvalid);
    recordScalar("dropped early", droppedEarly);
    recordScalar("dropped flow", droppedFlow);
    recordScalar("dropped deadline", droppedDeadline);
    recordScalar("dropped duplicate", droppedDuplicate);
    recordScalar("dropped gap timeout", droppedGapTimeout);
    recordScalar("dropped reorder buffer", droppedBuffer);
    queueing::PacketFilterBase::finish();
}

} // namespace inet
