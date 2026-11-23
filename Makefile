OMNETPP_ROOT ?= /home/yishi/workspace/omnet++/omnetpp-6.4.0
INET_ROOT ?= /home/yishi/workspace/inet-4.7.0
CXX := g++
CXXFLAGS := -std=c++17 -O3 -DNDEBUG=1 -g1 -fPIC -I$(OMNETPP_ROOT)/include -I$(INET_ROOT)/src -include inet/common/precompiled_release.h -DOMNETPPLIBS_IMPORT -DINET_EXPORT -fno-omit-frame-pointer -fopenmp
LDFLAGS := -shared -L$(OMNETPP_ROOT)/lib -L$(INET_ROOT)/out/gcc-release/src -Wl,--no-as-needed
LDLIBS := -lINET -loppenvir -loppsim -lstdc++ -fopenmp

all: libQciQbv.so

libQciQbv.so: out/TimingAdmissionUdpSourceApp.o out/TimingUdpSinkApp.o
	$(CXX) $(LDFLAGS) -o $@ $^ $(LDLIBS) -Wl,-rpath,$(OMNETPP_ROOT)/lib -Wl,-rpath,$(INET_ROOT)/out/gcc-release/src

out/TimingAdmissionUdpSourceApp.o: src/TimingAdmissionUdpSourceApp.cc
	mkdir -p out
	$(CXX) $(CXXFLAGS) -c -o $@ $<

out/TimingUdpSinkApp.o: src/TimingUdpSinkApp.cc
	mkdir -p out
	$(CXX) $(CXXFLAGS) -c -o $@ $<

clean:
	rm -rf out libQciQbv.so
