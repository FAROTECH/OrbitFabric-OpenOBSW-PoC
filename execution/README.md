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

## Stage 4.4 unified PoC pipeline validation

The PoC can now run the complete local validation chain through a single wrapper:

    python3 tools/validate_poc_pipeline.py --opensvf-repo ../opensvf --openobsw-repo ../openobsw --clean

The wrapper runs the existing generation and validation steps in sequence:

    python3 tools/generate_poc_artifacts.py
    python3 tools/validate_opensvf_srdb_xtce.py --opensvf-repo ../opensvf
    python3 tools/generate_poc_xtce_mdb.py --opensvf-repo ../opensvf
    python3 tools/validate_openobsw_contract_adapter.py --openobsw-repo ../openobsw --clean
    python3 tools/validate_openobsw_ping_smoke.py

This stage only unifies local validation. It does not introduce a YAMCS runtime campaign, Renode setup, Docker workflow, CI workflow, telemetry runtime mapping, event runtime mapping, or housekeeping runtime mapping.

## Stage 5.0 closed-loop campaign boundary

The next planned validation boundary is recorded as a campaign descriptor:

    execution/campaigns/poc_ping_closed_loop.yaml

Validate the descriptor with:

    python3 tools/validate_stage5_campaign_plan.py

This stage does not execute YAMCS, Renode, Docker, CI, OpenOBSW telemetry runtime mapping, OpenOBSW event runtime mapping, or housekeeping runtime mapping.

It only makes the next closed-loop OpenSVF/YAMCS campaign boundary explicit and machine-checkable.

## Stage 5.1 local evidence bundle

The current Stage 5 campaign boundary can produce a local machine-readable evidence bundle:

    python3 tools/generate_stage5_evidence_bundle.py --opensvf-repo ../opensvf --openobsw-repo ../openobsw --clean

The generated evidence is intentionally local and ignored by Git:

    execution/evidence/poc_ping_closed_loop_evidence.json

This does not execute YAMCS, Renode, Docker, CI, telemetry runtime mapping, event runtime mapping, or housekeeping runtime mapping.

The Stage 5 evidence bundle also records local provenance and SHA-256 hashes for the campaign descriptor and generated artifacts, so the evidence can be traced to a specific repository state and artifact set.
