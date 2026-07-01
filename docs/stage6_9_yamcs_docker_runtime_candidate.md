# Stage 6.9 - Docker-based YAMCS Runtime Candidate

Status: local PoC-side runtime candidate implemented, closed-loop TM/TC still pending.

## Goal

Stage 6.9 introduces a reproducible PoC-side Docker/YAMCS runtime candidate for the generated XTCE/MDB artifact.

The validated handoff is:

    OrbitFabric mission model / mapping
    -> generated SRDB
    -> generated XTCE/MDB
    -> mounted into YAMCS 5.12.6
    -> imported by YAMCS
    -> visible through YAMCS HTTP on port 8090

## Rationale

Stage 6.8 made the generated MDB path explicit and machine-checkable.

Stage 6.9 turns that handoff into a runnable YAMCS candidate while preserving the PoC boundary:

    PoC repo owns the candidate Docker/YAMCS execution material
    OpenSVF remains the reference pattern for YAMCS configuration
    OpenSVF proper is not modified
    OpenOBSW proper is not modified
    OrbitFabric Core does not emit XTCE directly

## Implementation

Stage 6.9 adds:

    execution/yamcs/Dockerfile.candidate
    execution/yamcs/docker-compose.candidate.yml
    execution/yamcs/etc/yamcs.yaml
    execution/yamcs/etc/yamcs.opensvf.yaml
    execution/yamcs/etc/processor.yaml
    execution/yamcs/mdb/README.md
    execution/yamcs/README.md
    tools/validate_stage6_9_yamcs_docker_runtime_candidate.py

The candidate uses:

    YAMCS version: 5.12.6
    HTTP port: 8090
    TM TCP port: 10015
    TC UDP port: 10025
    MDB container path: /yamcs/mdb/poc_xtce_mdb.xml
    YAMCS instance: opensvf

## Validation boundary

Static validation:

    python3 tools/validate_stage6_9_yamcs_docker_runtime_candidate.py

Runtime smoke validation:

    python3 tools/validate_stage6_9_yamcs_docker_runtime_candidate.py --runtime-smoke

The runtime smoke validates:

    Docker Compose build/start
    YAMCS HTTP API readiness
    YAMCS API version 5.12.6
    default YAMCS instance opensvf
    PoC MDB mounted inside the container
    PoC MDB imported by YAMCS
    expected MDB markers present

## Explicit non-goals

Stage 6.9 does not claim:

    live OpenSVF YamcsBridge execution
    live OpenOBSW telemetry delivery into YAMCS
    closed-loop TC/TM execution
    Renode execution
    CI execution
    production deployment hardening

A YAMCS log message about the TM TCP data link being unable to connect to 127.0.0.1:10015 is expected when no OpenSVF/YamcsBridge runtime is active.

That live bridge belongs to a later runtime integration stage.

## Known benign runtime warnings

During the Stage 6.9 runtime smoke test, YAMCS may also report that stream configuration is present both in the instance configuration and in the processor configuration.

This is non-blocking for the candidate because Stage 6.9 validates MDB import, YAMCS startup, HTTP readiness, and the declared OpenSVF-like TM/TC boundary. Stream configuration cleanup remains a refinement for a later live runtime integration stage.

## Why the candidate is PoC-side

A direct OpenSVF Dockerfile-based runtime was not used as the Stage 6.9 implementation baseline in this checkout, because the current OpenSVF Dockerfile failed before YAMCS launch during its internal XTCE generation step.

The PoC therefore keeps the candidate container local to execution/yamcs/, preserving the OpenSVF YAMCS runtime pattern while avoiding changes to OpenSVF proper.
