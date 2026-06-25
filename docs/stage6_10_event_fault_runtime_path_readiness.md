# Stage 6.10 - Event/Fault Runtime Path Readiness

Stage 6.10 validates the current readiness state of the event/fault runtime path without claiming a live event runtime smoke.

The target path is:

```text
eps.voltage_out_of_bounds
-> fault/event materialization
-> TM(5,3)
-> OpenSVF/YAMCS event or alarm visibility
```

## Purpose

The PoC already defines the event and fault semantics in the OrbitFabric Mission Model and maps the event to a PUS Service 5 warning event in the PoC allocation layer.

This stage records and validates the current technical boundary before adding a real runtime smoke for the event/fault path.

## What is validated

Stage 6.10 validates that:

* the Mission Model defines `eps.voltage_out_of_bounds`;
* the Mission Model fault `eps.voltage_out_of_bounds_fault` emits that event;
* the fault condition is tied to `eps.obc.bus_voltage_mv > 3500` with three debounce samples;
* the PoC mapping allocates the event as `OF_EVENT_VOLTAGE_OUT_OF_BOUNDS`;
* the PoC mapping assigns event ID `0x5001`;
* the PoC mapping assigns PUS Service 5, subtype 3, corresponding to `TM(5,3)`;
* the generated flight contract exposes `OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001`;
* OpenOBSW exposes PUS Service 5 event reporting capability;
* OpenOBSW maps medium severity to `TM(5,3)`;
* OpenOBSW encodes the event ID as the first two bytes of the S5 application data;
* OpenSVF exposes a YAMCS bridge boundary on TM TCP port `10015` and TC UDP port `10025`;
* OpenSVF exposes a PUS Service 5 helper that can generate `TM(5,3)`;
* the Stage 6.9 YAMCS candidate preserves the OpenSVF-like TM/TC boundary.

## Current gap

Stage 6.10 does not close the runtime path.

The following items remain pending:

* no live OpenOBSW trigger currently demonstrates `eps.obc.bus_voltage_mv` crossing the PoC warning threshold and calling `obsw_s5_report()` for `OF_EVENT_VOLTAGE_OUT_OF_BOUNDS`;
* no live OpenSVF campaign currently observes that specific `TM(5,3)` event from OpenOBSW;
* no live YAMCS candidate currently receives that specific event through `YamcsBridge`;
* the current PoC SRDB artifact remains parameter-centric and does not emit the event as a first-class SRDB event definition;
* the current PoC MDB import candidate is not yet an event/fault runtime evidence path;
* the YAMCS processor candidate keeps generated events and parameter alarm checks disabled.

## Boundary

Stage 6.10 does not:

* modify OpenSVF;
* modify OpenOBSW;
* modify OrbitFabric Core;
* add a live OpenSVF `YamcsBridge` execution path;
* add live OpenOBSW telemetry delivery into YAMCS;
* claim closed-loop event/fault runtime execution;
* claim YAMCS alarm visibility for the specific event;
* replace OpenSVF SRDB, XTCE or YAMCS responsibilities;
* make OrbitFabric Core emit XTCE directly.

## Validation

Run:

```bash
python3 tools/validate_stage6_10_event_fault_runtime_path_readiness.py
```

Expected result:

```text
Stage 6.10 event/fault runtime path readiness: PASS
```

## Next step

The next technical step should be a real runtime smoke only after the readiness gap is deliberately closed.

A future stage should validate one of these paths:

```text
OpenOBSW threshold trigger
-> obsw_s5_report(OBSW_S5_MEDIUM, OF_EVENT_VOLTAGE_OUT_OF_BOUNDS, ...)
-> TM(5,3)
-> OpenSVF observation
```

or:

```text
OpenSVF PUS Service 5 injection
-> YamcsBridge TM TCP
-> YAMCS packet/event visibility
```

The first path is stronger because it proves OpenOBSW event materialization. The second path is useful only as an intermediate YAMCS visibility probe.
