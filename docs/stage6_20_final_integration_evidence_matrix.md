# Stage 6.20 - Final Integration Evidence Matrix

## PoC completion statement

Stage 6.20 closes the current OrbitFabric/OpenOBSW/OpenSVF/YAMCS PoC vertical slice.

This stage does not introduce a new runtime path. Instead, it consolidates the runtime evidence accumulated in Stages 6.17, 6.18, and 6.19 into a final traceability and evidence matrix.

The completed PoC slice covers:

* telemetry visibility: live OpenOBSW `TM(3,25)` housekeeping telemetry observed through OpenSVF and classified in YAMCS as `TM_3_25_HK`;
* event reporting visibility: live OpenOBSW `TM(5,3)` event telemetry carrying `OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001` at full-packet `raw[17:19]`, observed through OpenSVF and classified in YAMCS as `TM_5_3_Event`;
* command-response direction: YAMCS-originated `TC(17,1)` released through `tc-out`, received by the OpenSVF `YamcsBridge`, forwarded to `OBCEmulatorAdapter.receive_tc(...)`, handled by live OpenOBSW `obsw_sim`, and observed back in YAMCS as `TM(1,1)`, `TM(17,2)`, and `TM(1,7)`.

This completes the PoC-level integration claim: selected OrbitFabric contract elements can be traced from OrbitFabric Mission Model terminology and generated artifacts into OpenOBSW runtime behavior, OpenSVF transport/adapter observation, and YAMCS command/telemetry visibility.

## What this PoC now proves

The current PoC proves a minimal but complete end-to-end integration slice across OrbitFabric, OpenOBSW, OpenSVF, and YAMCS.

It proves that selected OrbitFabric contract elements can be represented in generated flight-side and ground-side artifacts, exercised or observed through OpenOBSW host-sim runtime, transported or intercepted through OpenSVF, and made visible in YAMCS through MDB classification, packet archive visibility, command history, and `tm-in`/`tc-out` links.

The proof is intentionally narrow and representative. It covers one housekeeping telemetry row, one event-reporting row, and one command-response row. It is therefore suitable as a PoC completion point, not as a claim of full production integration.

## What remains outside this PoC

The current PoC does not claim production completeness.

In particular, it does not claim:

* full production mission integration;
* hardware target execution;
* Renode or STM32 execution;
* production FDIR behavior;
* production command authorization, authentication, security, or queueing policy;
* complete coverage of all OpenOBSW services;
* complete coverage of all OpenSVF campaign capabilities;
* a production-ready OrbitFabric contract generator;
* a complete mission-wide telemetry, command, event, fault, limit, and parameter dictionary.

Those items belong to a post-PoC productionization, coverage expansion, or hardening phase. They are intentionally kept outside the Stage 6.20 claim.

The final matrix validates that the already-proven paths are represented consistently across:

- OrbitFabric Mission Model terminology;
- PoC mapping and allocation artifacts;
- generated flight-software contract artifacts;
- generated SRDB / XTCE / YAMCS MDB artifacts;
- OpenOBSW runtime evidence;
- OpenSVF observed path evidence;
- YAMCS observed path evidence;
- stage validators and documentation.

## Evidence rows

| Evidence row | OrbitFabric / PoC entity | Flight contract evidence | SRDB / YAMCS evidence | Runtime evidence | YAMCS evidence |
| --- | --- | --- | --- | --- | --- |
| Housekeeping telemetry | `eps.obc.bus_voltage_mv` | `generated_artifacts/flight_software/mission_contract.h` exposes `obc_bus_voltage_mv` | `generated_artifacts/ground_segment/poc_srdb.yaml` and generated MDB expose `eps_obc_bus_voltage_mv` and `TM_3_25_HK` | Stage 6.17 observes live OpenOBSW `TM(3,25)` through `OBCEmulatorAdapter` | Stage 6.17 validates YAMCS `tm-in`, archive visibility, and MDB classification as `TM_3_25_HK` |
| Ping command path | `ping` / Are-You-Alive representative command | PoC contract and MDB expose the representative command mapping | generated MDB exposes `/opensvf/TC_17_1_AreYouAlive` and response containers `TM_1_1_Accept`, `TM_17_2_Pong`, `TM_1_7_Complete` | Stage 6.19 observes YAMCS-originated `TC(17,1)` received by OpenSVF and forwarded into live OpenOBSW `obsw_sim` through `OBCEmulatorAdapter.receive_tc(...)` | Stage 6.19 validates YAMCS command history, `tm-in`, archive visibility, and MDB classification of the response telemetry |
| Event / warning telemetry | `eps.voltage_out_of_bounds` | `generated_artifacts/flight_software/mission_contract.h` exposes `OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001` | generated MDB exposes `TM_5_3_Event`, `of_event_id`, and bit offset 136 for the live OpenOBSW packet layout | Stage 6.18 builds OrbitFabric-enabled OpenOBSW `obsw_sim`, uses the controlled host-sim `TC(8,1)` trigger, and observes live `TM(5,3)` with `event_id=0x5001` at full-packet `raw[17:19]` | Stage 6.18 validates YAMCS `tm-in`, archive visibility, and MDB classification as `TM_5_3_Event` |

## Stage evidence consumed

Stage 6.20 consumes the evidence produced by the following stages:

- Stage 6.11: PUS Service 5 event MDB projection.
- Stage 6.12: contract packet visibility readiness for HK and event packets.
- Stage 6.15: representative YAMCS archive and MDB classification.
- Stage 6.16: real OpenSVF `YamcsBridge` TM path into YAMCS.
- Stage 6.17: live OpenOBSW HK TM path into YAMCS.
- Stage 6.18: live OpenOBSW event TM path into YAMCS.
- Stage 6.19: YAMCS-originated TC direction into live OpenOBSW host-sim execution.

## Live path closure summary

### Telemetry direction

    live OpenOBSW TM(3,25)
    -> OpenSVF OBCEmulatorAdapter
    -> real OpenSVF YamcsBridge
    -> YAMCS tm-in
    -> YAMCS archive
    -> MDB classification as TM_3_25_HK

### Event direction

    controlled host-sim TC(8,1) trigger
    -> OpenOBSW OrbitFabric S8 hook
    -> live OpenOBSW TM(5,3)
    -> OpenSVF OBCEmulatorAdapter
    -> real OpenSVF YamcsBridge
    -> YAMCS tm-in
    -> YAMCS archive
    -> MDB classification as TM_5_3_Event

### Command direction

    YAMCS REST command release for /opensvf/TC_17_1_AreYouAlive
    -> YAMCS StreamTcCommandReleaser
    -> YAMCS tc-out UdpTcDataLink
    -> real OpenSVF YamcsBridge TC UDP reception
    -> YamcsBridge.get_tc()
    -> OBCEmulatorAdapter.receive_tc(...)
    -> live OpenOBSW obsw_sim
    -> TM(1,1), TM(17,2), TM(1,7)
    -> YAMCS tm-in
    -> YAMCS command history
    -> YAMCS packet archive
    -> MDB classification as TM_1_1_Accept, TM_17_2_Pong, TM_1_7_Complete

## Explicit non-claims

Stage 6.20 intentionally does not claim:

- production mission integration;
- hardware target execution;
- Renode or STM32 execution;
- production deployment hardening;
- production FDIR behavior;
- production voltage-threshold detection;
- production commanding authorization;
- production command queueing policy;
- production command security;
- a generic OrbitFabric event routing table;
- a stable Core-native XTCE backend;
- a Studio dependency;
- broader OpenOBSW/OpenSVF integration beyond the validated PoC paths.

## Validator role

The Stage 6.20 validator is static and evidence-oriented.

It does not rerun the long Docker runtime campaigns. Those runtime campaigns remain owned by their dedicated validators:

- `tools/validate_stage6_17_live_openobsw_hk_tm_yamcs_path_probe.py`
- `tools/validate_stage6_18_live_openobsw_event_yamcs_path_probe.py`
- `tools/validate_stage6_19_yamcs_tc_direction_closure.py`

Instead, the Stage 6.20 validator verifies that the evidence matrix is backed by the expected artifacts, markers, validators, generated MDB containers, command definitions, runtime claims, and explicit non-claims.
