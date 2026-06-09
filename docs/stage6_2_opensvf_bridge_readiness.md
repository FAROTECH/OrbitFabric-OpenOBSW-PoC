# Stage 6.2 OpenSVF bridge readiness wrapper

This document defines the Stage 6.2 OpenSVF bridge readiness boundary for the OrbitFabric/OpenOBSW/OpenSVF PoC.

Stage 6.1 established that OpenSVF already provides the relevant pipe-mode mechanism and that the likely next step is a PoC-side wrapper before runtime execution.

Stage 6.2 turns that conclusion into a concrete readiness surface.

## Core decision

Stage 6.2 treats OpenSVF pipe mode as the candidate bridge.

It does not introduce a custom bridge process.

The purpose of this stage is to prepare and validate the PoC-side configuration surface needed to exercise the existing OpenSVF bridge in a later runtime smoke stage.

If the next runtime smoke confirms that OpenSVF pipe mode can drive the OrbitFabric-enabled OpenOBSW host simulator and expose the expected TC/TM path, the bridge question from Stage 6.0 is resolved without additional bridge code.

## Target future chain

The target future chain remains:

    OrbitFabric Mission Model
    -> generated flight and ground artifacts
    -> generated OpenSVF SRDB / XTCE-YAMCS MDB
    -> PoC-side OpenSVF spacecraft configuration
    -> OpenSVF pipe mode
    -> OrbitFabric-enabled OpenOBSW host simulator
    -> TC(17,1)
    -> TM(1,1), TM(17,2), TM(1,7)
    -> machine-readable runtime evidence

## Added readiness surface

Stage 6.2 introduces:

    execution/opensvf/poc_spacecraft.yaml
    execution/opensvf/poc_runtime_inputs.yaml
    execution/campaigns/poc_runtime_ping_plan.yaml

The spacecraft wrapper configures the OpenSVF pipe-mode side:

    obsw.type: pipe
    obsw.binary: ../../../openobsw/build_stage4_orbitfabric/sim/obsw_sim

The runtime input manifest records the PoC-side artifacts that will be needed by the first runtime smoke:

    generated_artifacts/flight_software/mission_contract.h
    generated_artifacts/ground_segment/poc_srdb.yaml
    execution/generated/poc_xtce_mdb.xml

The runtime ping plan records the first expected command/telemetry path:

    OF_CMD_PING
    TC(17,1)
    TM(1,1)
    TM(17,2)
    TM(1,7)

## External SRDB / XTCE handling

Stage 6.2 does not invent an unsupported SRDB, XTCE, MDB or YAMCS field inside `spacecraft.yaml`.

The generated MDB is tracked as a PoC runtime input until OpenSVF's accepted configuration surface for external SRDB/MDB paths is proven.

This keeps the PoC honest:

    spacecraft.yaml owns the OpenSVF pipe-mode host-sim configuration.
    poc_runtime_inputs.yaml owns the generated artifact inventory.
    poc_runtime_ping_plan.yaml owns the first planned runtime command/telemetry path.

## Validation approach

The Stage 6.2 validator checks:

    the PoC-side spacecraft configuration exists
    the wrapper uses OpenSVF pipe mode
    the wrapper points to the expected OpenOBSW host-sim path
    the wrapper does not invent unsupported SRDB/XTCE/YAMCS fields
    the runtime input manifest references the expected generated artifacts
    the runtime ping plan records TC(17,1)
    the expected TM sequence is TM(1,1), TM(17,2), TM(1,7)
    runtime execution remains disabled
    OpenSVF SpacecraftValidator can validate the PoC-side spacecraft YAML when OpenSVF is available

The validator does not run:

    YAMCS
    OpenSVF runtime campaign
    OpenOBSW host simulator
    command injection
    telemetry observation
    Docker
    CI
    Renode

## Explicit OpenSVF preflight assumption

Stage 6.2 assumes that OpenSVF exposes:

    svf.config.validator.SpacecraftValidator
    SpacecraftValidator.validate_or_raise()

for preflight validation of the PoC-side `spacecraft.yaml`.

This was not established by Stage 6.1. Stage 6.1 only checked the OpenSVF source facts around `SpacecraftLoader` and `tools/generate_xtce.py`.

For that reason, the `SpacecraftValidator` usage is recorded as an explicit Stage 6.2 preflight assumption in the runtime input manifest. If Stage 6.3 fails at this point, the failure should be interpreted as a validation API or local OpenSVF checkout assumption issue, not as a runtime bridge failure.

## Stage 6.3 timing note

The current `simulation.stop_time: 1.0` value is a readiness placeholder.

Stage 6.2 does not execute the runtime path. Stage 6.3 may need to tune this value according to the OpenOBSW scheduler tick rate and the observed TC/TM round-trip latency.

## Current boundary

Stage 6.2 does not introduce:

    YAMCS runtime execution
    command injection runtime
    telemetry runtime observation
    Docker workflow
    CI workflow
    Renode execution
    OpenSVF proper changes
    OpenOBSW proper changes
    custom bridge process
    runtime bridge implementation

Stage 6.2 is the readiness step before the first runtime smoke attempt.
