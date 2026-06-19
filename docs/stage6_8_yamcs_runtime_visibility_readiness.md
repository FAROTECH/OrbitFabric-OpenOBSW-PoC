# Stage 6.8 - YAMCS/MDB Runtime Visibility Readiness

Stage 6.8 starts the YAMCS runtime visibility track without yet claiming a full
YAMCS runtime execution.

The purpose of this stage is to verify that the PoC already has a clean,
runtime-facing MDB handoff point that can be used by a later YAMCS import or
launch step.

## Scope

This stage validates that:

* the PoC-side runtime input manifest exists;
* the manifest points to the generated XTCE/MDB artifact;
* the generated XTCE/MDB artifact exists;
* the generated MDB is valid XML;
* the generated MDB contains the known housekeeping visibility markers;
* the manifest still explicitly declares that YAMCS runtime execution is not yet active.

## Runtime visibility markers

The current minimum markers are:

* `eps_obc_bus_voltage_mv`;
* `TM_3_25_HK`.

These markers are intentionally the same ones already used by the SRDB/XTCE
generation validation path. Stage 6.8 does not add new telemetry semantics.

## Boundary

Stage 6.8 does not:

* launch YAMCS;
* introduce Docker;
* modify OpenSVF;
* modify OpenOBSW;
* make OrbitFabric Core emit XTCE directly;
* claim closed-loop YAMCS runtime execution;
* validate the event/fault runtime path.

The intended result is a clean and repeatable readiness check before moving to
an actual YAMCS runtime import or launch path.

## Validation

Run:

    python3 tools/validate_stage6_8_yamcs_runtime_visibility.py

Expected result:

    Stage 6.8 YAMCS/MDB runtime visibility readiness: PASS
