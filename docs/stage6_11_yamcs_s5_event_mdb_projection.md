# Stage 6.11 - YAMCS PUS Service 5 Event MDB Projection

Stage 6.11 closes the Stage 6.10 MDB visibility gap for the selected PoC event/fault path.

The target path is:

```text
eps.voltage_out_of_bounds
-> OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001
-> PUS Service 5 subtype 3
-> TM(5,3)
-> YAMCS MDB container visibility
```

## Purpose

Stage 6.10 validated that the event/fault path is technically ready, while reporting the generated MDB `TM(5,3)` marker as readiness state.

Stage 6.11 adds a PoC-side MDB projection so that the generated local YAMCS MDB exposes the selected PUS Service 5 warning event.

## What is projected

The local MDB generation wrapper now projects:

* `of_event_id` as the OrbitFabric event identifier carried in PUS Service 5 event reports;
* `TM_5_3_Event` as the XTCE/YAMCS sequence container for PUS Service 5 subtype 3;
* `pus_svc == 5` as the service restriction;
* `pus_subsvc == 3` as the subservice restriction;
* the event ID field at bit offset 88, after the 6-byte CCSDS primary header and the 5-byte PUS-C secondary header.

The projected event is:

```text
OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001
eps.voltage_out_of_bounds
```

## Boundary

OpenSVF remains the source of the base XTCE/MDB generation.

Stage 6.11 applies a local PoC-side projection in `tools/generate_poc_xtce_mdb.py` after OpenSVF has generated the base MDB.

Stage 6.11 does not:

* modify OpenSVF;
* modify OpenOBSW;
* modify OrbitFabric Core;
* run a live OpenSVF `YamcsBridge`;
* run live OpenOBSW event delivery into YAMCS;
* claim YAMCS alarm triggering for the selected event;
* claim closed-loop event/fault runtime execution.

## Validation result

Stage 6.11 validates that the generated MDB contains:

```text
of_event_id
TM_5_3_Event
OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001
eps.voltage_out_of_bounds
```

Stage 6.10 then reports:

```text
Generated MDB TM(5,3) marker: present
```

The Stage 6.9 Docker/YAMCS runtime smoke validates that YAMCS imports the updated MDB successfully.

The observed YAMCS import cardinality after the projection is:

```text
4 parameters, 8 tm containers, 2 commands
```

This is consistent with the added `of_event_id` parameter and `TM_5_3_Event` sequence container.

## Validation

Run:

```bash
python3 tools/generate_poc_xtce_mdb.py
python3 -m py_compile tools/validate_stage6_11_yamcs_s5_event_mdb_projection.py
python3 tools/validate_stage6_11_yamcs_s5_event_mdb_projection.py
python3 tools/validate_stage6_10_event_fault_runtime_path_readiness.py
python3 tools/validate_stage6_9_yamcs_docker_runtime_candidate.py
python3 tools/validate_stage6_9_yamcs_docker_runtime_candidate.py --runtime-smoke
python3 tools/validate_stage6_8_yamcs_runtime_visibility.py
git diff --check
```

Expected result:

```text
Stage 6.11 YAMCS PUS Service 5 event MDB projection: PASS
Stage 6.10 event/fault runtime path readiness: PASS
Stage 6.9 Docker-based YAMCS runtime candidate: PASS
Stage 6.8 YAMCS/MDB runtime visibility readiness: PASS
```

## Next step

The next technical step remains a runtime smoke for the event/fault path.

Possible future paths are:

```text
OpenSVF PUS Service 5 injection
-> YamcsBridge TM TCP
-> YAMCS packet/event visibility
```

or:

```text
OpenOBSW threshold trigger
-> obsw_s5_report(OBSW_S5_MEDIUM, OF_EVENT_VOLTAGE_OUT_OF_BOUNDS, ...)
-> TM(5,3)
-> OpenSVF observation
-> YAMCS visibility
```

The second path is stronger because it proves OpenOBSW event materialization. The first path is a useful intermediate YAMCS visibility probe.
