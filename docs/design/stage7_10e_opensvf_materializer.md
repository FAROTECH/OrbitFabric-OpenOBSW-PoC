# Stage 7.10e: OpenSVF Materialization from Verification Projection Plan

## Objective

Stage 7.10e introduces the first deterministic materializer from the validated
Verification Projection Plan to native OpenSVF campaign assets.

The semantic interpretation boundary remains upstream.

The materializer consumes:

```text
verification_projection_plan.json
OpenSVF spacecraft execution template
```

and produces:

```text
procedures/verification_projection_procedure.py
campaigns/verification_projection_campaign.yaml
opensvf/spacecraft.yaml
materialization_manifest.json
```

The materializer does not read:

```text
OrbitFabric scenario YAML
Mission Model YAML
Core Integration Input Set
Projection Profile
OpenOBSW SRDB
```

It therefore cannot reinterpret source semantics.

## Materialization rule

The only executable v0 plan operations are already frozen by Stage 7.10b:

```text
pus_tc
expect_pus_tm
```

The mapping is mechanical:

```text
pus_tc
  -> ctx.tc(...)

expect_pus_tm
  -> ctx.expect_tm(...)
```

No other plan information becomes an OpenSVF runtime action.

## Plan gate

Only:

```text
status = executable_subset
```

may be materialized.

A blocked plan is rejected with:

```text
OFI-VPROJ-MAT-001
```

An executable plan with zero operations is also rejected because it would
produce a meaningless PASS procedure with no target verification activity.

## APID authority

The generated `ctx.tc()` APID is taken only from:

```text
operation.resolved.apid
```

For the Stage 7.10 reference plan this is:

```text
0x010
```

This intentionally differs from the hand-written Stage 7.9 procedure, which
used `0x001`.

Stage 7.10 does not copy the Stage 7.9 constant.

It consumes the resolved plan value.

## OpenSVF execution policy

`expect_pus_tm` requires an execution timeout in OpenSVF.

The Verification Projection Plan intentionally does not encode a timeout
because timeout is execution policy rather than OrbitFabric scenario meaning.

Stage 7.10e therefore defines a materializer-owned default:

```text
tm_expectation_timeout_s = 5.0
```

The value is recorded in `materialization_manifest.json`.

Changing it does not change the source scenario semantics or Profile target
mapping.

## Scenario time

Scenario `t` is not materialized.

The generated procedure contains no:

```text
ctx.wait(...)
ctx.schedule_tc(...)
PUS Service 11 scheduling
```

The manifest records:

```text
scenario_time_interpretation = provenance_only
```

## Native step traceability

Every generated OpenSVF procedure step begins with the corresponding plan
operation ID.

Example:

```text
op-0001: Send PUS TC(17,1)
op-0002: Expect PUS TM(1,1)
op-0003: Expect PUS TM(17,2)
op-0004: Expect PUS TM(1,7)
```

OpenSVF records procedure step names in its native CampaignReport.

This creates a direct traceability chain:

```text
plan operation ID
      ->
generated Procedure.step name
      ->
native CampaignReport step name
```

No OpenSVF modification is required.

## Spacecraft configuration

The materializer receives a PoC-owned OpenSVF spacecraft execution template.

It does not interpret or rewrite the template.

The bytes are copied exactly to:

```text
opensvf/spacecraft.yaml
```

The reference template keeps the established pipe runtime arrangement:

```text
obsw.type = pipe
obsw.binary = ../bin/obsw_sim
simulation.dt = 0.1
simulation.stop_time = 10.0
simulation.realtime = true
```

The next runtime stage will place the built OpenOBSW host simulator in the
bundle `bin` directory. Because the spacecraft file is materialized at
`bundle/opensvf/spacecraft.yaml`, the relative runtime path is
`../bin/obsw_sim`.

## Campaign metadata

The generated campaign contains one generated procedure.

No requirement is invented from OrbitFabric scenario expectations.

The generated Procedure therefore uses:

```text
requirement = ""
```

Requirement projection remains outside Stage 7.10 v0.

## Materialization manifest

The Integration Package owns a deterministic materialization manifest recording:

```text
source plan SHA-256
source scenario identity and SHA-256
materializer execution policy
generated artifact SHA-256 values
copied spacecraft SHA-256
plan operation -> OpenSVF native primitive mapping
plan operation -> procedure step index mapping
```

The manifest is traceability evidence for the generated target assets.

It is not an OpenSVF native evidence report.

## Determinism

Given byte-identical:

```text
Verification Projection Plan
spacecraft template
materializer policy
```

the materializer must produce byte-identical:

```text
procedure
campaign
spacecraft copy
materialization manifest
```

No absolute filesystem path is written into generated artifacts.

## Stage 7.10e acceptance

Stage 7.10e is accepted when:

1. the real Stage 7.10d reference plan is generated;
2. only an `executable_subset` plan is accepted;
3. the reference plan produces one OpenSVF procedure and one campaign;
4. the spacecraft template is copied byte-identically;
5. `op-0001` materializes to `ctx.tc`;
6. the generated TC uses APID `0x010`;
7. the generated TC uses service 17, subtype 1;
8. `op-0002` through `op-0004` materialize to `ctx.expect_tm`;
9. the three generated TM expectations preserve plan order;
10. the TM timeout is materializer-owned and recorded as 5.0 seconds;
11. no `ctx.wait` is generated from scenario time;
12. no `schedule_tc` or PUS Service 11 behavior is generated;
13. each native step name starts with its plan operation ID;
14. OpenSVF `CampaignRunner.from_yaml` discovers the generated Procedure;
15. dry execution of the generated native Procedure emits the exact resolved
    TC/TM call sequence;
16. the materialization manifest covers every plan operation;
17. repeated materialization is byte-identical;
18. OrbitFabric and OpenSVF working trees remain unchanged;
19. no OpenOBSW runtime execution occurs in this stage;
20. unit tests pass.

## Files

Stage 7.10e adds:

```text
docs/design/stage7_10e_opensvf_materializer.md
execution/opensvf/stage7_10_spacecraft.yaml
integration_package/adapter/opensvf_materializer.py
integration_package/tests/test_opensvf_materializer.py
tools/validate_stage7_10e_opensvf_materializer.py
```

Generated procedure, campaign and manifest files are not committed.

They are deterministic outputs of the materializer and will be generated in a
temporary execution bundle by acceptance tooling.
