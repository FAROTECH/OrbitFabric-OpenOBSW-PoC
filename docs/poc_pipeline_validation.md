# PoC pipeline validation

This document describes the Stage 4.4 unified local validation runner for the OrbitFabric/OpenOBSW PoC.

The runner lives in the PoC repository and orchestrates the existing generation and validation tools.

It does not modify OpenSVF.
It does not modify OpenOBSW.
It does not introduce a YAMCS runtime campaign, Renode setup, Docker workflow, CI workflow, telemetry runtime mapping, event runtime mapping, or housekeeping runtime mapping.

## Command

From the PoC repository:

    python3 tools/validate_poc_pipeline.py --opensvf-repo ../opensvf --openobsw-repo ../openobsw --clean

## Validation sequence

The runner executes the following steps in order:

    python3 tools/generate_poc_artifacts.py
    python3 tools/validate_opensvf_srdb_xtce.py --opensvf-repo ../opensvf
    python3 tools/generate_poc_xtce_mdb.py --opensvf-repo ../opensvf
    python3 tools/validate_openobsw_contract_adapter.py --openobsw-repo ../openobsw --clean
    python3 tools/validate_openobsw_ping_smoke.py

## Expected result

The expected final result is:

    OrbitFabric/OpenOBSW PoC pipeline validation: PASS

This validates the current model-first chain:

    OrbitFabric Mission Model
    -> generated mission_contract.h
    -> generated OpenSVF SRDB
    -> XTCE/YAMCS MDB generation
    -> OpenOBSW host-sim adapter consumption
    -> command-path smoke validation

## Current boundary

This stage only unifies local validation.

It does not execute a closed-loop OpenSVF/YAMCS campaign and does not introduce OpenOBSW telemetry or event runtime mapping.
