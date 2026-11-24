package qci_qbv;

import inet.queueing.contract.IPacketFilter;

simple ClippedQciIngressFilter like IPacketFilter
{
    parameters:
        @class(inet::ClippedQciIngressFilter);
        bool backpressure = default(false);
        double cycle @unit(s) = default(1ms);
        double windowStart @unit(s) = default(900us);
        double windowDuration @unit(s) = default(100us);
        double earlyTolerance @unit(s) = default(100us);
        double lateTolerance @unit(s) = default(50us);
        double deadline @unit(s) = default(1ms);
        double maxQueueDelay @unit(s) = default(100us);
        double serviceTime @unit(s) = default(10us);
        double reorderTimeout @unit(s) = default(80us);
        int maxReorderBuffer = default(16);
        int flowBurstFrames = default(1);
        int initialSequence = default(0);
        int payloadLength @unit(B) = default(1000B);
        bool useFlowMeter = default(true);
        bool applyEarlyTolerance = default(true);
        bool useMaxQueueDelay = default(true);
    gates:
        input in;
        output out;
}
