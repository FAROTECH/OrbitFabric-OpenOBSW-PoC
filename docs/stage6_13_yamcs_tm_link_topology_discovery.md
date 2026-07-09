# Stage 6.13 - YAMCS TM Link Topology Discovery

Stage 6.13 records the actual OpenSVF/YAMCS TM link topology that must be respected before attempting YAMCS packet classification or packet visibility claims.

## Purpose

Stage 6.12 introduced a local representative packet probe and showed that representative TM packet bytes can be built for:

```text
TM(3,25)
TM(5,3)
```

A follow-up runtime inspection showed that the Stage 6.9 YAMCS candidate exposes the Docker host port `10015`, but the YAMCS `tm-in` data link itself remains unavailable when no OpenSVF `YamcsBridge` is running.

Stage 6.13 therefore clarifies the real topology:

```text
OpenSVF YamcsBridge
-> TCP server on 127.0.0.1:10015
-> raw PUS TM packets

YAMCS TcpTmDataLink
-> TCP client
-> connects to 127.0.0.1:10015
-> consumes TM from the bridge
```

## Evidence

OpenSVF requirements define the bridge boundary:

```text
YamcsBridge exposes a TCP server on port 10015 for TM downlink.
YamcsBridge exposes a UDP server on port 10025 for TC uplink.
YamcsBridge forwards raw PUS TM packets from the OBC emulator to YAMCS.
YamcsBridge receives PUS TC packets from YAMCS via UDP.
```

The OpenSVF implementation confirms that:

```text
YAMCS connects as TCP client to the SVF bridge.
The bridge binds/listens on 127.0.0.1:10015.
The bridge accepts the YAMCS TM connection.
The bridge sends raw TM bytes with sendall().
The bridge receives TC bytes on UDP port 10025.
```

The OpenSVF integration tests simulate the same topology:

```text
test_bridge_accepts_yamcs_tm_connection
test_bridge_sends_tm_to_yamcs
test_bridge_receives_tc_from_yamcs
```

The local PoC YAMCS candidate mirrors the OpenSVF YAMCS link configuration:

```text
tm-in:
  class: org.yamcs.tctm.TcpTmDataLink
  host: 127.0.0.1
  port: 10015
  packetPreprocessorClassName: org.yamcs.pus.PusPacketPreprocessor

tc-out:
  class: org.yamcs.tctm.UdpTcDataLink
  host: 127.0.0.1
  port: 10025
```

## Runtime observation

With only the Stage 6.9 YAMCS candidate running and no OpenSVF `YamcsBridge`, the YAMCS link API reports:

```text
tm-in status: UNAVAIL
tm-in detailedStatus: Not connected to 127.0.0.1:10015
tm-in dataInCount: 0
```

This is expected. It means the YAMCS candidate is configured as a client and is waiting for the OpenSVF bridge-side TM TCP server.

## Boundary

Stage 6.13 does not:

* modify OpenSVF;
* modify OpenOBSW;
* modify OrbitFabric Core;
* run a live OpenSVF `YamcsBridge`;
* run live OpenOBSW packet generation;
* claim YAMCS packet consumption;
* claim MDB packet classification;
* claim parameter/event visibility;
* claim closed-loop runtime execution.

## Validation

Run:

```bash
python3 tools/validate_stage6_13_yamcs_tm_link_topology_discovery.py
```

Optional runtime observation can be repeated by starting the Stage 6.9 YAMCS candidate and inspecting the link API:

```bash
docker compose -f execution/yamcs/docker-compose.candidate.yml up --build -d
curl -sS http://localhost:8090/api/links/opensvf/tm-in
docker compose -f execution/yamcs/docker-compose.candidate.yml down --remove-orphans
```

Expected no-bridge observation:

```text
status: UNAVAIL
detailedStatus: Not connected to 127.0.0.1:10015
dataInCount: 0
```

## Next step

The next stronger step is not host-side TCP injection.

The next stronger step is one of:

```text
OpenSVF YamcsBridge
-> YAMCS tm-in link becomes available
-> raw representative TM packets delivered through the bridge
-> YAMCS MDB classification evidence
```

or:

```text
minimal PoC-side bridge-compatible TM producer
-> listens on 127.0.0.1:10015 where YAMCS expects the bridge
-> accepts YAMCS TcpTmDataLink connection
-> sends representative TM(3,25) and TM(5,3)
-> observes YAMCS link dataInCount/classification evidence
```

The first path is architecturally stronger because it follows the real OpenSVF runtime topology.
