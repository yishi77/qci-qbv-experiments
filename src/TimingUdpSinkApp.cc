#include "inet/applications/udpapp/UdpBasicApp.h"
#include "inet/applications/base/ApplicationPacket_m.h"
#include "inet/common/TimeTag_m.h"

namespace inet {

class TimingUdpSinkApp : public UdpBasicApp
{
  protected:
    cOutVector delayVector;
    cStdDev delayStats;
    simtime_t cycle;
    simtime_t windowStart;

    virtual void initialize(int stage) override
    {
        UdpBasicApp::initialize(stage);
        if (stage == INITSTAGE_LOCAL) {
            cycle = par("cycle");
            windowStart = par("windowStart");
            delayVector.setName("endToEndDelay");
            delayVector.setUnit("s");
            delayStats.setName("endToEndDelay");
        }
    }

    virtual void processPacket(Packet *packet) override
    {
        simtime_t generationTime = SIMTIME_ZERO;
        bool hasGenerationTime = false;
        auto creationTimeTag = packet->findTag<CreationTimeTag>();
        if (creationTimeTag != nullptr) {
            generationTime = creationTimeTag->getCreationTime();
            hasGenerationTime = true;
        }
        else if (packet->getTotalLength() >= B(1)) {
            auto applicationPacket = packet->peekAtFront<ApplicationPacket>();
            if (applicationPacket != nullptr) {
                generationTime = windowStart + applicationPacket->getSequenceNumber() * cycle;
                hasGenerationTime = true;
            }
        }
        if (hasGenerationTime) {
            simtime_t delay = simTime() - generationTime;
            delayVector.record(delay);
            delayStats.collect(delay.dbl());
        }
        delete packet;
        numReceived++;
    }

    virtual void finish() override
    {
        if (delayStats.getCount() > 0) {
            recordScalar("mean end-to-end delay", delayStats.getMean());
            recordScalar("maximum end-to-end delay", delayStats.getMax());
            recordScalar("minimum end-to-end delay", delayStats.getMin());
        }
        UdpBasicApp::finish();
    }
};

Define_Module(TimingUdpSinkApp);

} // namespace inet
