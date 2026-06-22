# Stage 6.9 Docker-based YAMCS Runtime Candidate

This directory contains the PoC-side YAMCS runtime candidate for Stage 6.9.

It is intentionally local to the PoC repository. It does not modify OpenSVF or OpenOBSW.

## Purpose

Stage 6.9 moves the PoC from MDB readiness to a concrete YAMCS-visible runtime candidate:

    generated XTCE/MDB
    -> mounted into a YAMCS 5.12.6 container
    -> imported by YAMCS
    -> visible through the YAMCS HTTP service on port 8090

## Boundary

This candidate validates:

    YAMCS 5.12.6 container startup
    PoC MDB mount
    PoC MDB import
    HTTP API readiness on 8090
    OpenSVF-like TM/TC configuration
    TM TCP port 10015
    TC UDP port 10025
    PusPacketPreprocessor

It does not validate:

    live OpenSVF YamcsBridge execution
    live OpenOBSW telemetry delivery into YAMCS
    closed-loop TC/TM execution
    Renode
    CI
    production deployment hardening

## Generate the MDB

    python3 tools/generate_poc_xtce_mdb.py --opensvf-repo ../opensvf

## Static validation

    python3 tools/validate_stage6_9_yamcs_docker_runtime_candidate.py

## Runtime smoke validation

    python3 tools/validate_stage6_9_yamcs_docker_runtime_candidate.py --runtime-smoke

The runtime smoke starts the candidate with Docker Compose, waits for:

    http://localhost:8090/api/

checks the YAMCS API response, checks that the MDB was imported, and then stops the container unless --keep-running is used.

## Manual launch

    docker compose -f execution/yamcs/docker-compose.candidate.yml up --build

Open:

    http://localhost:8090

Stop:

    docker compose -f execution/yamcs/docker-compose.candidate.yml down

## Expected non-goal warning

If no OpenSVF/YamcsBridge runtime is active, YAMCS may log a connection-refused message for the TM TCP link on port 10015.

That is expected for Stage 6.9. The live bridge belongs to a later runtime integration stage.

YAMCS may also report that stream configuration is present both in the instance configuration and in the processor configuration. This is non-blocking for the candidate because Stage 6.9 validates MDB import, YAMCS startup, HTTP readiness, and the declared OpenSVF-like TM/TC boundary. Stream configuration cleanup remains a refinement for a later live runtime integration stage.
