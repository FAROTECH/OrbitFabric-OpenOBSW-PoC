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
