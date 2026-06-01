# OpenOBSW Host-Sim Ping Smoke Validation

This document records the Stage 4.3 minimal command-path smoke validation.

## Scope

Stage 4.3 validates the first executable command path after the OpenOBSW contract adapter handoff.

The validated path is:

  generated_artifacts/flight_software/mission_contract.h
  -> OpenOBSW optional OrbitFabric contract adapter
  -> OF_CMD_PING
  -> TC(17,1)
  -> OpenOBSW host simulator
  -> TM(1,1), TM(17,2), TM(1,7)

This is still narrower than a full OpenSVF/YAMCS closed-loop campaign.

## Boundary

The smoke test does not modify OpenOBSW.

The smoke test does not modify OpenSVF.

The smoke test does not execute YAMCS.

The smoke test does not introduce S3 housekeeping runtime mapping or S5 event runtime mapping.

It only verifies that the command-side contract path can reach the existing OpenOBSW S17 handler through the host simulator.

## Protocol shape

The OpenOBSW host simulator reads type-prefixed frames on stdin.

For TC uplink, the outer simulator frame is:

  0x01
  uint16 big-endian payload length
  TC packet bytes

The TC packet bytes are a minimal CCSDS/PUS-C TC space packet:

  6-byte CCSDS primary header
  5-byte PUS-C secondary header

For the current ping smoke test, the PUS service/subservice fields are:

  service: 17
  subservice: 1

The expected telemetry responses are emitted as host-sim TM frames:

  0x04
  uint16 big-endian payload length
  TM packet bytes

The smoke validator checks for:

  TM(1,1)
  TM(17,2)
  TM(1,7)

and accepts the final sync byte:

  0xFF

## PoC-side validation wrapper

The PoC repository provides:

  tools/validate_openobsw_ping_smoke.py

Expected sequence from the PoC repository root:

  python3 tools/generate_poc_artifacts.py
  python3 tools/validate_openobsw_contract_adapter.py --openobsw-repo ../openobsw --clean
  python3 tools/validate_openobsw_ping_smoke.py

Expected final result:

  OpenOBSW host-sim ping smoke validation: PASS

## Current status

Stage 4.3 proves a minimal command-side execution path:

  OrbitFabric generated contract
  -> OpenOBSW adapter-enabled host simulator
  -> existing S17 ping handler
  -> expected S1/S17 telemetry responses

The next meaningful expansion should be selected deliberately.

Recommended candidates are:

  document Stage 5 closed-loop validation boundary
  prepare OpenSVF/YAMCS campaign wiring
  defer S3/S5 runtime mapping until the command path is fully documented
