# Stage 6.14 - YAMCS Bridge-Compatible TM Producer Smoke

Stage 6.14 validates the YAMCS TM link direction discovered in Stage 6.13 by running a minimal bridge-compatible TM producer next to the YAMCS candidate.

## Purpose

Stage 6.13 established the correct topology:

```text
OpenSVF YamcsBridge
-> TCP server on 127.0.0.1:10015

YAMCS TcpTmDataLink
-> TCP client to 127.0.0.1:10015
```

Stage 6.14 introduces a PoC-side temporary producer that matches the OpenSVF `YamcsBridge` TM-side topology:

```text
stage6_14_bridge_tm_producer.py
-> listens on 127.0.0.1:10015
-> accepts the YAMCS TcpTmDataLink connection
-> sends representative raw TM packets
```

The producer is run as a Docker Compose sidecar with:

```text
network_mode: service:yamcs
```

This makes the producer's `127.0.0.1:10015` visible exactly where the YAMCS container expects the bridge-side TM server.

## Representative packets

The smoke sends representative raw TM packets for:

```text
TM(3,25) - housekeeping visibility side
TM(5,3)  - event visibility side
```

The representative packets use the same PUS-C secondary header version byte (`0x20`) as Stage 6.12.

The `TM(5,3)` packet carries the representative PoC event identifier:

```text
of_event_id = 0x5001
```

## Runtime evidence

The expected successful link observation is:

```text
tm-in status: OK
tm-in detailedStatus: OK, connected to 127.0.0.1:10015
tm-in dataInCount >= 2
```

This is stronger than Stage 6.12 because it demonstrates that YAMCS `TcpTmDataLink` connects to a bridge-compatible producer and consumes TM packets through the correct direction.

## Boundary

Stage 6.14 does not:

* modify OpenSVF;
* modify OpenOBSW;
* modify OrbitFabric Core;
* run the real OpenSVF `YamcsBridge`;
* run live OpenOBSW packet generation;
* claim live OpenSVF/OpenOBSW closed-loop execution;
* claim YAMCS MDB packet classification;
* claim parameter/event extraction through the YAMCS API;
* claim production deployment hardening.

## Validation

Run:

```bash
python3 tools/validate_stage6_14_yamcs_bridge_compatible_tm_producer.py
```

The validator:

```text
generates the PoC XTCE/MDB
starts the YAMCS candidate
starts the bridge-compatible TM producer sidecar
waits for YAMCS API readiness
observes /api/links/opensvf/tm-in
requires status=OK and dataInCount>=2
stops the containers
```

## Next step

The next stronger stage should move from a synthetic bridge-compatible producer to the real OpenSVF runtime bridge path:

```text
OpenSVF YamcsBridge
-> YAMCS tm-in OK
-> OpenOBSW/OpenSVF packet source
-> YAMCS MDB classification / packet viewer evidence
```
