# Execution Material

This directory is reserved for local PoC execution material, validation runners, generated campaign artifacts, and future evidence.

## Current Stage 3b output

The current local generated XTCE/YAMCS MDB output is:

  execution/generated/poc_xtce_mdb.xml

Generate it with:

  python3 tools/generate_poc_xtce_mdb.py --opensvf-repo ../opensvf

The generated file is intentionally local and ignored by Git.

## Source inputs

The current generation path starts from:

  generated_artifacts/ground_segment/poc_srdb.yaml

The SRDB artifact is generated from:

  orbitfabric_models/mission/
  orbitfabric_models/poc_slice.yaml

using:

  python3 tools/generate_poc_artifacts.py

## Validation

Before using generated execution material, run:

  python3 tools/validate_opensvf_srdb_xtce.py --opensvf-repo ../opensvf

Then generate the local MDB:

  python3 tools/generate_poc_xtce_mdb.py --opensvf-repo ../opensvf

## Current boundary

This directory does not yet contain a YAMCS runtime campaign, Renode setup, Docker workflow, CI workflow, or OpenOBSW runtime execution evidence.

Those belong to later stages.

## Stage 4.2 OpenOBSW contract adapter validation

The PoC can validate the OpenOBSW optional OrbitFabric contract adapter from this workspace.

First regenerate the PoC artifacts:

  python3 tools/generate_poc_artifacts.py

Then validate the OpenOBSW default and OrbitFabric-enabled host-sim builds:

  python3 tools/validate_openobsw_contract_adapter.py --openobsw-repo ../openobsw --clean

The validation wrapper checks that OpenOBSW still builds and tests normally with the adapter disabled, and that the generated mission_contract.h can be consumed when the adapter is enabled.

This does not execute a YAMCS runtime campaign and does not introduce OpenOBSW telemetry/event runtime mapping.

## Stage 4.3 OpenOBSW host-sim ping smoke validation

After validating the OpenOBSW contract adapter build handoff, the PoC can run a minimal host-sim command-path smoke test.

First regenerate the PoC artifacts and validate the OpenOBSW adapter builds:

  python3 tools/generate_poc_artifacts.py
  python3 tools/validate_openobsw_contract_adapter.py --openobsw-repo ../openobsw --clean

Then run the ping smoke validation:

  python3 tools/validate_openobsw_ping_smoke.py

The smoke test sends TC(17,1) through the OpenOBSW host-sim type-frame protocol and checks for:

  TM(1,1)
  TM(17,2)
  TM(1,7)

This validates the minimal command-side path. It does not run YAMCS and does not introduce OpenOBSW telemetry or event runtime mapping.
