# Stage 5 closed-loop campaign plan

This document defines the next validation boundary after the Stage 4 PoC pipeline.

Stage 4 proves the local model-first chain up to OpenOBSW host-sim command-path smoke evidence.

Stage 5 will move toward a closed-loop OpenSVF/YAMCS campaign, but this step does not implement that runtime campaign yet.

## Current validated chain

The current validated chain is:

    OrbitFabric Mission Model
    -> generated mission_contract.h
    -> generated OpenSVF SRDB
    -> XTCE/YAMCS MDB generation through OpenSVF
    -> OpenOBSW host-sim adapter consumption
    -> command-path smoke validation

The current unified validation command is:

    python3 tools/validate_poc_pipeline.py --opensvf-repo ../opensvf --openobsw-repo ../openobsw --clean

Expected result:

    OrbitFabric/OpenOBSW PoC pipeline validation: PASS

## Stage 5 intent

Stage 5 should transform the existing command-path smoke evidence into a future ground-visible validation campaign.

The target chain is:

    generated XTCE/YAMCS MDB
    + OpenOBSW host-sim command path
    + expected TM sequence
    -> OpenSVF/YAMCS campaign evidence

## Campaign descriptor

The planned campaign boundary is recorded in:

    execution/campaigns/poc_ping_closed_loop.yaml

The descriptor records:

    input artifacts
    validated Stage 4 steps
    command path
    expected telemetry
    future campaign target
    explicit non-goals

## Expected command path

The first command path remains:

    OF_CMD_PING
    -> TC(17,1)
    -> OpenOBSW host simulator
    -> TM(1,1), TM(17,2), TM(1,7)

This path was intentionally selected before expanding into housekeeping telemetry or warning event runtime mapping.

## Boundary

This stage does not introduce:

    YAMCS runtime execution
    Renode execution
    Docker workflow
    CI workflow
    OpenOBSW telemetry runtime mapping
    OpenOBSW event runtime mapping
    housekeeping runtime mapping
    OpenSVF proper changes
    OpenOBSW proper changes

The purpose is to make the next closed-loop campaign boundary explicit, reviewable and machine-checkable before implementing runtime campaign execution.

## Acceptance criteria

This planning stage is complete when:

    the campaign descriptor exists
    the descriptor references the generated Stage 4 artifacts
    the descriptor records the expected command and telemetry path
    a validator checks the descriptor structure
    the unified Stage 4 pipeline still passes
