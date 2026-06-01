# OpenOBSW Contract Adapter Integration

This document records the Stage 4.2 handoff between the PoC-generated OrbitFabric flight contract and the OpenOBSW host simulator.

## Scope

Stage 4.2 documents and validates the OpenOBSW-side contract consumption point that is now present in upstream OpenOBSW.

The relevant generated PoC artifact is:

  generated_artifacts/flight_software/mission_contract.h

The OpenOBSW-side integration point is optional and host-sim scoped.

It maps the generated OrbitFabric command identifier:

  OF_CMD_PING

to the existing OpenOBSW PUS route:

  TC(17,1)

## Current integration chain

The current chain is:

  generated_artifacts/flight_software/mission_contract.h
  -> OpenOBSW optional host-sim OrbitFabric adapter
  -> OF_CMD_PING
  -> TC(17,1)
  -> existing OpenOBSW S17 ping handler

The generated contract remains contract-only.

It does not contain runtime behavior, PUS framing, transport logic, scheduling logic, or command execution code.

OpenOBSW remains responsible for runtime command handling.

## OpenOBSW-side behavior

The adapter is disabled by default.

It is enabled with:

  OBSW_ENABLE_ORBITFABRIC_CONTRACT=ON

The generated contract directory is provided with:

  ORBITFABRIC_CONTRACT_DIR=<path-to-generated_artifacts/flight_software>

When enabled, OpenOBSW includes the generated mission_contract.h and builds the host-sim adapter.

The adapter translates OF_CMD_PING into a route descriptor containing:

  apid: 0xFFFF
  service: 17
  subservice: 1

The host simulator then applies that mapping to the existing TC(17,1) route.

The route is found by scanning the route table for service 17 and subservice 1, rather than relying on a positional route index.

## PoC-side validation wrapper

The PoC repository provides this validation wrapper:

  tools/validate_openobsw_contract_adapter.py

The wrapper validates two builds:

  default OpenOBSW build with OrbitFabric adapter disabled
  OpenOBSW host-sim build with OrbitFabric adapter enabled

The wrapper does not modify OpenOBSW.

It only configures, builds, and runs OpenOBSW tests from the PoC workspace.

## Expected validation sequence

From the PoC repository root:

  python3 tools/generate_poc_artifacts.py
  python3 tools/validate_openobsw_contract_adapter.py --openobsw-repo ../openobsw --clean

Expected final result:

  OpenOBSW OrbitFabric contract adapter validation: PASS

## Boundary

Stage 4.2 does not introduce:

  OpenOBSW telemetry runtime mapping
  S3 housekeeping runtime integration
  S5 warning event runtime integration
  OpenSVF changes
  YAMCS runtime execution
  Renode execution
  Docker workflow
  CI workflow
  OrbitFabric Core changes

Those belong to later stages.

## Current status

At this stage, the PoC has a validated command-side contract consumption point:

  OrbitFabric generated flight contract
  -> OpenOBSW optional host-sim adapter
  -> existing OpenOBSW TC(17,1) path

This is intentionally narrower than full closed-loop validation.

The next integration step should build on this validated command path before expanding into telemetry and event runtime mapping.
