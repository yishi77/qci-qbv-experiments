package qci_qbv;

import inet.applications.udpapp.UdpBasicApp;

simple TimingUdpSinkApp extends UdpBasicApp
{
    parameters:
        @class(inet::TimingUdpSinkApp);
        double cycle @unit(s) = default(1ms);
        double windowStart @unit(s) = default(900us);
}
