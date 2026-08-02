# Stage 6.16 - Real OpenSVF YamcsBridge TM Path Probe

## Purpose

Stage 6.16 replaces the Stage 6.14/6.15 bridge-compatible producer with the real OpenSVF `YamcsBridge`.

The target chain is:

```text
real OpenSVF YamcsBridge
-> TCP server on 127.0.0.1:10015
-> YAMCS tm-in TcpTmDataLink client
-> YAMCS packet archive API
-> YAMCS MDB packet classification
```

This closes the gap between a PoC-side bridge-compatible producer and the actual OpenSVF bridge implementation.

## Runtime setup

The stage runs a small driver sidecar in the same Docker network namespace as YAMCS. The driver mounts the sibling OpenSVF checkout and imports:

```text
../opensvf/src/svf/ground/yamcs_bridge.py
```

The driver then instantiates the real `YamcsBridge`, starts it, and sends representative TM packets through the bridge's `send_tm()` API.

The driver provides a strict minimal store stub only to satisfy the `YamcsBridge` constructor in this standalone TM-path probe. The stub is intentionally fail-fast: if the bridge unexpectedly accesses OpenSVF campaign/store state, the validator fails rather than masking that dependency.

The packets are:

```text
TM(3,25) - housekeeping side
TM(5,3)  - event side, with event ID 0x5001
```

The packets use the same PUS-C secondary header version byte (`0x20`) as Stages 6.12, 6.14 and 6.15.

## Soft-skip rule

The sibling OpenSVF checkout is optional for general PoC validation.

If `../opensvf` is absent, the validator emits a `NOTICE` and soft-skips the real OpenSVF runtime probe instead of failing with a path-based file error.

When `../opensvf` is present, the real OpenSVF YamcsBridge runtime probe is executed.

## Pass criteria when OpenSVF is present

The validator requires all of the following:

```text
real OpenSVF YamcsBridge starts
YAMCS tm-in status OK
YAMCS tm-in dataInCount >= 2
MDB container TM_3_25_HK visible through API
MDB container TM_5_3_Event visible through API
Representative raw TM(3,25) packet archived
Representative raw TM(5,3) packet archived
Packet archive name classified as TM_3_25_HK
Packet archive name classified as TM_5_3_Event
```

## Claims

This stage claims only:

```text
Real OpenSVF YamcsBridge runtime observed: true
YAMCS TcpTmDataLink packet consumption through real OpenSVF YamcsBridge: true
YAMCS packet archive raw packet visibility: true
YAMCS MDB container definitions visible via API: true
YAMCS MDB packet classification observed via archive name: true
```

## Explicit non-claims

This stage does not claim live OpenOBSW packet generation.

This stage does not claim OpenSVF campaign closed-loop execution.

This stage does not claim YAMCS TC command path execution.

This stage does not claim live event/fault generation by OpenOBSW.

This stage does not claim closed-loop runtime execution.

This stage does not claim YAMCS parameter/event API extraction.

This stage does not claim production deployment hardening.
