# Stage 6.12 - YAMCS Contract Packet Visibility Probe

Stage 6.12 introduces a local PoC-side representative packet probe for the YAMCS candidate.

The target path is:

```text
Representative TM packet bytes
-> YAMCS candidate TCP TM input
-> PusPacketPreprocessor boundary
-> generated MDB contract
-> TM(3,25) and TM(5,3) packet visibility readiness
```

## Purpose

Stage 6.11 projected the selected PUS Service 5 warning event into the generated local YAMCS MDB.

Stage 6.12 verifies that the current YAMCS candidate boundary is ready to accept representative packets for both sides of the original vertical slice:

```text
TM(3,25) -> telemetry side
TM(5,3)  -> event side
```

This stage deliberately stays below the live OpenSVF/YamcsBridge and OpenOBSW runtime layers.

## What is validated

The validator checks:

* the generated MDB contains `PUS_Packet`;
* `pus_svc` is located at bit offset 56;
* `pus_subsvc` is located at bit offset 64;
* `TM_3_25_HK` restricts `pus_svc == 3` and `pus_subsvc == 25`;
* `TM_5_3_Event` restricts `pus_svc == 5` and `pus_subsvc == 3`;
* `of_event_id` is located at bit offset 88 in `TM_5_3_Event`;
* the YAMCS candidate exposes a TCP TM input on `127.0.0.1:10015`;
* representative TM packet bytes can be constructed for `TM(3,25)` and `TM(5,3)`;
* the representative `TM(5,3)` packet carries `of_event_id = 0x5001`.

When YAMCS is running, the validator also attempts to write the representative packets toward the currently exposed TCP boundary.

## Boundary

Stage 6.12 does not:

* modify OpenSVF;
* modify OpenOBSW;
* modify OrbitFabric Core;
* run a live OpenSVF `YamcsBridge`;
* generate packets from live OpenOBSW execution;
* claim YAMCS MDB classification observed via API;
* claim YAMCS parameter/event visibility via API;
* claim closed-loop runtime execution.

A successful TCP send attempt to `127.0.0.1:10015` only validates that the PoC probe could write representative packet bytes toward the currently exposed TCP boundary.

It does not, by itself, prove that the YAMCS `TcpTmDataLink` read the bytes, that MDB container classification occurred, or that parameter extraction happened. The observed YAMCS log still shows `TcpTmDataLink [tm-in] Cannot open or read TM socket 127.0.0.1: 10015: Connection refused`, so the live TM producer/data-link topology remains pending.

## Validation

Run the static/readiness probe with:

```bash
python3 tools/generate_poc_xtce_mdb.py
python3 -m py_compile tools/validate_stage6_12_yamcs_contract_packet_visibility_probe.py
python3 tools/validate_stage6_12_yamcs_contract_packet_visibility_probe.py
```

Expected result when YAMCS is not running:

```text
Packet injection attempted: false
Stage 6.12 YAMCS contract packet visibility probe: PASS
```

Expected result when the Stage 6.9 YAMCS candidate is running and the exposed TCP boundary accepts the probe connection:

```bash
docker compose -f execution/yamcs/docker-compose.candidate.yml up --build -d
python3 tools/validate_stage6_12_yamcs_contract_packet_visibility_probe.py
docker compose -f execution/yamcs/docker-compose.candidate.yml down --remove-orphans
```

```text
Packet injection attempted: true
Stage 6.12 YAMCS contract packet visibility probe: PASS
```

## Validation result

Observed local result with YAMCS stopped:

```text
Packet injection attempted: false
Stage 6.12 YAMCS contract packet visibility probe: PASS
```

Observed local result with the Stage 6.9 YAMCS candidate running:

```text
Packet injection attempted: true
Stage 6.12 YAMCS contract packet visibility probe: PASS
```

## Next step

The next stronger step is to observe actual YAMCS MDB classification or parameter/event visibility for the representative packets.

Possible future paths are:

```text
Representative packet injector
-> YAMCS TCP TM input
-> YAMCS processor
-> MDB container classification evidence
-> parameter/event visibility evidence
```

and then:

```text
OpenSVF YamcsBridge
-> YAMCS TCP TM input
-> YAMCS packet/event visibility
```

The final stronger path remains:

```text
OpenOBSW threshold trigger
-> obsw_s5_report(OBSW_S5_MEDIUM, OF_EVENT_VOLTAGE_OUT_OF_BOUNDS, ...)
-> TM(5,3)
-> OpenSVF observation
-> YamcsBridge delivery
-> YAMCS visibility
```
