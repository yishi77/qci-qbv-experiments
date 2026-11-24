package qci_qbv;

import inet.common.Module;
import inet.networklayer.configurator.contract.IL3NetworkConfigurator;
import inet.networklayer.configurator.contract.INetworkConfigurator;
import inet.node.ethernet.EthernetLink;
import inet.node.tsn.TsnDevice;
import inet.node.tsn.TsnSwitch;
import inet.visualizer.contract.IIntegratedVisualizer;

network QciQbvMultiSwitch extends Module
{
    parameters:
        bool hasGlobalArp = default(true);
        *.ipv4.arp.typename = default(hasGlobalArp ? "GlobalArp" : "Arp");
    submodules:
        nstClient: TsnDevice {
            @display("p=150,100");
        }
        stClient: TsnDevice {
            @display("p=150,300");
        }
        switch1: TsnSwitch {
            @display("p=400,200");
        }
        switch2: TsnSwitch {
            @display("p=650,200");
        }
        switch3: TsnSwitch {
            @display("p=900,200");
        }
        server: TsnDevice {
            @display("p=1200,200");
        }
        visualizer: <default(firstAvailableOrEmpty("IntegratedCanvasVisualizer"))> like IIntegratedVisualizer if typename != "" {
            @display("p=80,80;is=s");
        }
        configurator: <default("Ipv4NetworkConfigurator")> like IL3NetworkConfigurator if typename != "" {
            @display("p=80,160;is=s");
        }
        macForwardingTableConfigurator: <default(hasGlobalArp ? "MacForwardingTableConfigurator" : "")> like INetworkConfigurator if typename != "" {
            @display("p=80,240;is=s");
        }
    connections:
        nstClient.ethg++ <--> EthernetLink <--> switch1.ethg++;
        stClient.ethg++ <--> EthernetLink <--> switch1.ethg++;
        switch1.ethg++ <--> EthernetLink <--> switch2.ethg++;
        switch2.ethg++ <--> EthernetLink <--> switch3.ethg++;
        switch3.ethg++ <--> EthernetLink <--> server.ethg++;
}
