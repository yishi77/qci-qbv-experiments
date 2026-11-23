package qci_qbv;

import inet.applications.udpapp.UdpBasicApp;

simple TimingAdmissionUdpSourceApp extends UdpBasicApp
{
    parameters:
        @class(inet::TimingAdmissionUdpSourceApp);
        string scenario = default("normal");
        string admissionMode = default("none");
        string ablationMode = default("proposed");
        string dropPolicy = default("none");
        int numFrames = default(200);
        int extraInsertCount = default(0);
        int flowBurstFrames = default(1);
        double cycle @unit(s) = default(1ms);
        double windowStart @unit(s) = default(900us);
        double earlyOffset @unit(s) = default(80us);
        double lateOffset @unit(s) = default(150us);
        double burstOffset @unit(s) = default(120us);
        double earlyTolerance @unit(s) = default(50us);
        double lateTolerance @unit(s) = default(50us);
        double deadline @unit(s) = default(1ms);
        double serviceTime @unit(s) = default(10us);
        double maxQueueDelay @unit(s) = default(1ms);
        bool applyEarlyTolerance = default(false);
}
