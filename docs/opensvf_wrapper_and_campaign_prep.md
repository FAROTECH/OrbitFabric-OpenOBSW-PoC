# OpenSVF Wrapper and Campaign Preparation

This document records the Stage 3b PoC wrapper boundary.

## Scope

Stage 3b turns the Stage 3 SRDB to XTCE validation path into a clearer local generation workflow.

The wrapper lives in this repository:

  tools/generate_poc_xtce_mdb.py

It consumes the generated PoC SRDB artifact:

  generated_artifacts/ground_segment/poc_srdb.yaml

It calls OpenSVF in place:

  OpenSVF SrdbLoader.load_mission()
  OpenSVF generate_xtce(srdb)

It writes a local generated XTCE/YAMCS MDB output:

  execution/generated/poc_xtce_mdb.xml

## Boundary

The wrapper does not modify OpenSVF.

The wrapper does not modify OpenOBSW.

The wrapper does not make OrbitFabric Core emit XTCE directly.

OpenSVF remains responsible for SRDB loading and XTCE generation. The PoC repository only provides the external mission SRDB path and the operational wrapper around the existing OpenSVF API.

## Relationship with Stage 3 validation

The existing validation script remains the check:

  python3 tools/validate_opensvf_srdb_xtce.py --opensvf-repo ../opensvf

The Stage 3b wrapper is the operational generation command:

  python3 tools/generate_poc_xtce_mdb.py --opensvf-repo ../opensvf

Both paths use the same generated SRDB input.

The validation script proves that the generated SRDB can be loaded and transformed into XTCE.

The generation wrapper writes the resulting XTCE/MDB XML to a reproducible local output path for future campaign preparation.

## Generated output policy

The output under execution/generated/ is local generated evidence.

It should not be committed unless the repository later decides to store generated campaign evidence explicitly.

For now, the source of truth remains:

  orbitfabric_models/mission/
  orbitfabric_models/poc_slice.yaml
  tools/generate_poc_artifacts.py
  generated_artifacts/ground_segment/poc_srdb.yaml
  tools/generate_poc_xtce_mdb.py

## Current minimal PoC checks

The current wrapper validates the same minimal Stage 3 expectations:

  eps_obc_bus_voltage_mv exists as an XTCE parameter
  TM_3_25_HK exists as an XTCE sequence container

These checks intentionally remain narrow.

Stage 3b is not a runtime validation campaign. It only prepares a clean generated XTCE/MDB artifact for later OpenSVF/YAMCS campaign work.

## Non-goals

Stage 3b does not perform:

  OpenSVF code changes
  OpenOBSW code changes
  OpenOBSW telemetry runtime mapping
  S3 housekeeping runtime integration
  S5 warning event runtime integration
  YAMCS runtime execution
  Renode integration
  Docker integration
  CI integration
  OrbitFabric Core changes
  Projection Profile implementation in OrbitFabric Core

## Expected command sequence

From the PoC repository root:

  python3 tools/generate_poc_artifacts.py
  python3 tools/validate_opensvf_srdb_xtce.py --opensvf-repo ../opensvf
  python3 tools/generate_poc_xtce_mdb.py --opensvf-repo ../opensvf

Expected local output:

  execution/generated/poc_xtce_mdb.xml
