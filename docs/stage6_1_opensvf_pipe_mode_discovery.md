# Stage 6.1 OpenSVF pipe mode discovery

This document defines the Stage 6.1 discovery boundary for the OrbitFabric/OpenOBSW/OpenSVF PoC.

Stage 6.0 identified the runtime campaign questions required before introducing an actual OpenSVF/YAMCS closed-loop runtime campaign.

Stage 6.1 narrows that discovery to the OpenSVF side:

- whether the existing OpenSVF pipe mode can connect to the OpenOBSW host simulator
- whether OpenSVF can reference a generated PoC SRDB path externally
- whether a small PoC-side configuration wrapper is required before runtime execution

## Purpose

The purpose of Stage 6.1 is to determine whether the next runtime campaign can be assembled using existing OpenSVF mechanisms, without modifying OpenSVF proper.

The target future chain remains:

    generated OrbitFabric/OpenSVF SRDB
    -> generated XTCE/YAMCS MDB
    -> OpenSVF local runtime
    -> OpenOBSW host simulator via pipe mode
    -> TC(17,1)
    -> TM(1,1), TM(17,2), TM(1,7)
    -> machine-readable runtime evidence

## Findings

### Finding 1: OpenSVF already has OBSW pipe mode

OpenSVF already supports an OBSW transport mode with:

    obsw.type: pipe
    obsw.binary: <path-to-obsw-sim>

The spacecraft loader validates `pipe`, `socket`, and `stub` transport modes.

For `pipe`, it requires `obsw.binary` and builds an `OBCEmulatorAdapter` around the configured binary path.

This means the OpenOBSW host simulator connection should not require a new bridge as the first assumption.

### Finding 2: SpacecraftLoader accepts an external spacecraft YAML path

OpenSVF `SpacecraftLoader.load()` accepts a spacecraft YAML path and builds a configured `SimulationMaster`.

This is enough to let the PoC provide its own wrapper/configuration YAML if needed.

### Finding 3: XTCE generation appears repo-local to OpenSVF SRDB

OpenSVF `tools/generate_xtce.py` currently loads SRDB baselines from:

    srdb/baseline/*.yaml

The current generator does not expose an obvious CLI argument such as:

    --srdb
    --srdb-path
    --baseline-dir
    --mission-srdb

for passing the PoC-generated SRDB externally.

### Finding 4: Stage 6.1 should stay PoC-side

Given the above, the correct next step is not an OpenSVF proper patch yet.

The correct next step is a PoC-side discovery/config wrapper boundary that records exactly what can be done with existing OpenSVF mechanisms and what still requires a wrapper.

## Stage 6.1 decision

Stage 6.1 concludes that:

    OpenSVF pipe mode should be reused for the OpenOBSW host-sim connection.
    A PoC-side config/wrapper is likely required for external SRDB/MDB discovery.
    OpenSVF proper should not be modified until this is proven necessary.

## Current boundary

Stage 6.1 does not introduce:

    YAMCS runtime execution
    command injection runtime
    telemetry runtime observation
    Docker workflow
    CI workflow
    Renode execution
    OpenSVF proper changes
    OpenOBSW proper changes
    runtime bridge implementation

This is a discovery and readiness stage only.
