# Stage 5 evidence bundle

This document describes the Stage 5.1 local evidence bundle generator.

Stage 5.0 defines the planned closed-loop campaign boundary.

Stage 5.1 captures local machine-readable evidence for the current validation boundary.

It does not execute YAMCS, Renode, Docker or CI.

It does not introduce OpenOBSW telemetry runtime mapping, OpenOBSW event runtime mapping, or housekeeping runtime mapping.

## Command

From the PoC repository:

    python3 tools/generate_stage5_evidence_bundle.py --opensvf-repo ../opensvf --openobsw-repo ../openobsw --clean

## Output

The generated evidence file is local and ignored by Git:

    execution/evidence/poc_ping_closed_loop_evidence.json

## Captured steps

The evidence bundle captures:

    python3 tools/validate_stage5_campaign_plan.py
    python3 tools/validate_poc_pipeline.py --opensvf-repo ../opensvf --openobsw-repo ../openobsw --clean

For each step, the bundle records:

    command
    start timestamp
    finish timestamp
    return code
    stdout
    stderr
    pass/fail result

## Expected result

The expected final result is:

    Stage 5 evidence bundle generation: PASS

## Boundary

This stage still remains local PoC evidence capture only.

It does not claim closed-loop YAMCS runtime execution.

It prepares the evidence structure that a future OpenSVF/YAMCS campaign can populate with real runtime campaign results.
