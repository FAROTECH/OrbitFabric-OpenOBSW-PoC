# Stage 7.10f: Final Runtime Acceptance

## Objective

Stage 7.10f closes the Stage 7.10 verification-projection path by executing the
generated OpenSVF procedure against the real OrbitFabric-derived OpenOBSW host
simulator.

No new projection semantics are introduced.

The acceptance run reconstructs both downstream branches from one authoritative
Core Integration Input Set and one Projection Profile.

## End-to-end flow

```text
OrbitFabric Mission Model
        |
        v
Core Integration Input Set
        |
        +-----------------------------+
        |                             |
        v                             v
Integration run_project        OrbitFabric scenario
        |                             |
        v                             v
flight contract               Stage 7.10d projector
SRDB contribution                    |
        |                             v
        |                  verification_projection_plan
        |                             |
        |                             v
        |                  Stage 7.10e materializer
        |                             |
        v                             v
target-owned SRDB             generated OpenSVF Procedure
composition                            |
        |                              |
        v                              |
OpenOBSW obsw_sim build                |
        |                              |
        +--------------+---------------+
                       |
                       v
              native CampaignRunner
                       |
                       v
              native CampaignReport
```

## Shared-input invariant

The flight branch and verification branch must consume the same:

```text
Core input_set_sha256
Projection Profile sha256
```

Stage 7.10f asserts this explicitly.

This avoids a false end-to-end result in which the runtime and verification
procedure were derived from different mission or target configurations.

## Flight branch

The acceptance run uses the existing Integration Package API:

```python
run_project(
    input_set_manifest,
    profile,
    output_dir=...
)
```

This regenerates:

```text
flight_software/mission_contract.h
obsw_srdb_contribution/*
```

No pre-existing Stage 7.4 bundle is required.

The generated contribution is composed with the pinned OpenOBSW base SRDB using
the target-owned:

```text
SRDBLoader
SRDBContributionLoader
SRDBComposer
SRDBMaterializer
```

The complete OpenOBSW host simulator is then built against:

```text
generated mission_contract.h
externally assembled SRDB
```

## Verification branch

The same Core Integration Input Set and Projection Profile feed the Stage 7.10d
projector.

The resulting validated plan feeds the Stage 7.10e OpenSVF materializer.

The plan is not reread semantically by the runtime acceptance harness.

## Execution environment boundary

Stages 7.10a through 7.10e define and validate host-side integration semantics,
projection and deterministic OpenSVF materialization.

Stage 7.10f is different: it executes the downstream OpenOBSW/OpenSVF runtime.

The pinned downstream projects document Linux/WSL2 as supported development and
execution environments. The final runtime acceptance therefore runs in Linux or
WSL2 and deliberately does not attempt to establish native Windows support.

This separation is intentional:

```text
OrbitFabric host portability
        !=
native portability of every downstream runtime
```

A downstream integration may impose its own execution-environment requirements
without restricting where OrbitFabric Core, projection or materialization can run.

The committed spacecraft template uses:

```text
../bin/obsw_sim
```

and the Stage 7.10f temporary runtime bundle uses the native Linux host-simulator
binary under:

```text
bin/obsw_sim
```

The acceptance validator fails fast on native Windows and directs the user to
Linux/WSL2.

## Runtime APID proof

The generated plan resolves:

```text
APID = 0x010
service = 17
subtype = 1
```

The generated OpenSVF procedure must therefore send:

```python
ctx.tc(service=17, subservice=1, apid=0x010)
```

Stage 7.10f proves that the actual OpenOBSW host runtime accepts that resolved
APID and returns the expected target verification sequence:

```text
TM(1,1)
TM(17,2)
TM(1,7)
```

This removes the manual `0x001` constant used by the historical Stage 7.9
procedure from the verification-projection path.

## Native evidence traceability

The Stage 7.10e materializer names native procedure steps with plan operation
IDs.

The final native OpenSVF CampaignReport must therefore contain:

```text
op-0001  PASS
op-0002  PASS
op-0003  PASS
op-0004  PASS
```

The acceptance harness compares the exact ordered IDs across:

```text
Verification Projection Plan operations
materialization_manifest operation_trace
native ProcedureResult steps
machine-readable CampaignReport JSON steps
```

This closes the traceability chain:

```text
OrbitFabric scenario
  -> plan operation
  -> generated OpenSVF step
  -> native CampaignReport step
```

## Semantic exclusions remain active

A successful Stage 7.10f does not change the v0 non-equivalences.

The following remain outside target projection:

```text
Core command_status
Core event expectation
Core scenario_status
scenario time scheduling
```

The three target TM expectations are still Profile-authored verification
obligations.

No OrbitFabric requirement ID is invented.

The generated native Procedure therefore keeps:

```text
requirement = ""
```

and the campaign declares no requirements.

## Repository integrity

The acceptance run records and compares working-tree state for:

```text
PoC
OrbitFabric Core
OpenOBSW
OpenSVF
```

It also fingerprints the OpenOBSW source `srdb/data` before and after execution.

All build, generated and runtime artifacts live in temporary directories except
the explicitly requested native campaign report JSON.

## Acceptance criteria

Stage 7.10f is accepted when:

1. the PoC is descended from the merged Stage 7.9 baseline;
2. OrbitFabric Core matches the pinned Stage 7.10 commit;
3. OpenOBSW matches the pinned target commit;
4. OpenSVF matches the pinned verification commit;
5. one Core Integration Input Set is generated successfully;
6. the flight and verification branches consume the same Core input SHA-256;
7. the flight and verification branches consume the same Profile SHA-256;
8. flight contract and SRDB contribution regenerate successfully;
9. the target-owned composed SRDB round-trips successfully;
10. the full OpenOBSW `obsw_sim` builds from the generated contract and
    assembled SRDB;
11. the verification plan regenerates as `executable_subset`;
12. the plan contains exactly `op-0001` through `op-0004`;
13. the OpenSVF bundle materializes from that plan;
14. the packaged runtime binary path resolves to the built `obsw_sim`;
15. the native CampaignRunner loads the generated Procedure;
16. the runtime sends the plan-resolved TC(17,1) using APID `0x010`;
17. native TM(1,1) verification passes;
18. native TM(17,2) verification passes;
19. native TM(1,7) verification passes;
20. the native procedure verdict is PASS;
21. all four native procedure steps are PASS;
22. plan, materialization manifest, native result and JSON evidence contain the
    same ordered operation IDs;
23. the campaign declares no invented OrbitFabric requirement;
24. scenario time remains provenance-only;
25. OpenOBSW source `srdb/data` remains byte-identical;
26. PoC, Core, OpenOBSW and OpenSVF working-tree states remain unchanged.

## Files

Stage 7.10f adds only:

```text
docs/design/stage7_10f_final_runtime_acceptance.md
tools/validate_stage7_10f_final_runtime_acceptance.py
```

It adds no new Integration Package production module.

This is intentional.

Stage 7.10 semantics, plan production and OpenSVF materialization are already
owned by Stages 7.10a through 7.10e. Stage 7.10f only proves the complete
runtime composition of those frozen responsibilities.
