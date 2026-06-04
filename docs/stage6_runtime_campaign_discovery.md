# Stage 6 runtime campaign discovery

This document defines the Stage 6.0 discovery boundary for the OrbitFabric/OpenOBSW/OpenSVF PoC.

Stage 5 made the next closed-loop campaign boundary explicit and evidence-ready.

Stage 6 starts the transition toward an actual runtime campaign, but this step still does not execute YAMCS, Renode, Docker or CI.

## Purpose

The purpose of Stage 6.0 is to identify what must be known before implementing a real closed-loop OpenSVF/YAMCS runtime campaign.

The target future chain is:

    generated XTCE/YAMCS MDB
    + local ground runtime
    + OpenOBSW host simulator
    + TC(17,1)
    + TM(1,1), TM(17,2), TM(1,7)
    -> machine-readable runtime evidence

## Discovery descriptor

The discovery descriptor is:

    execution/campaigns/poc_runtime_discovery.yaml

It records:

    baseline inputs
    runtime questions
    first runtime experiment
    explicit current boundary

## Baseline inputs

The discovery step starts from the Stage 5 artifacts:

    execution/campaigns/poc_ping_closed_loop.yaml
    tools/generate_stage5_evidence_bundle.py
    execution/generated/poc_xtce_mdb.xml
    generated_artifacts/ground_segment/poc_srdb.yaml
    generated_artifacts/flight_software/mission_contract.h

It also references the current OpenOBSW host simulator binary path used by the Stage 4/5 validation chain:

    ../openobsw/build_stage4_orbitfabric/sim/obsw_sim

## Runtime questions

The next implementation stage must resolve:

    how the generated XTCE/YAMCS MDB is loaded into a local ground runtime
    how OpenSVF should reference or drive that runtime
    how TC(17,1) should be represented in the campaign layer
    how the OpenOBSW host simulator should be connected to the ground runtime
    whether the current type-frame protocol can be bridged directly
    whether a small PoC bridge process is needed

## First runtime experiment

The first runtime experiment should be intentionally narrow:

    load or reference the generated MDB
    confirm visibility of the current telemetry/command identifiers
    do not yet expand into housekeeping runtime mapping
    do not yet expand into event runtime mapping

## Boundary

Stage 6.0 does not introduce:

    YAMCS runtime execution
    command injection runtime
    telemetry runtime observation
    Renode
    Docker
    CI
    OpenOBSW proper changes
    OpenSVF proper changes

This is a discovery and readiness stage only.
