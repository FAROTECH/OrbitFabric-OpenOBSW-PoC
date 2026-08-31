# Stage 7.10d: Minimal OrbitFabric Verification Projector

## Objective

Stage 7.10d implements the first producer of the Verification Projection Plan
frozen in Stages 7.10a through 7.10c.

The projector consumes:

```text
OrbitFabric scenario
Core Integration Input Set
Projection Profile
Integration Package target compatibility rules
```

and produces:

```text
verification_projection_plan.json
```

It does not import or materialize OpenSVF.

## Core scenario authority

The projector does not implement a second scenario parser or validator.

Scenario validation is delegated to the OrbitFabric Core `ScenarioLoader`
corresponding to the Core Integration Input Set producer version.

The loaded scenario Mission Model identity must match:

```text
Core input mission.id
Core input mission.model_version
```

The OrbitFabric runtime version used for scenario validation must match:

```text
Core input orbitfabric_version
```

A mismatch is a verification-projection provenance failure.

## Target compatibility authority

Before scenario projection, the projector reuses the existing Integration
Package target preflight:

```text
resolve_core_bindings
load_target_baseline
resolve_projection
```

This validates the Projection Profile against the already-established
OpenOBSW/OpenSVF reference target baseline.

The verification projector does not duplicate target compatibility logic.

## Reference scenario

Stage 7.10d adds:

```text
orbitfabric_models/scenarios/stage7_10_ping_verification.yaml
```

The scenario uses the existing PoC Mission Model and intentionally contains:

```text
initial mode NOMINAL

t=5
  command obc.ping
  expect command_status ACCEPTED

t=6
  expect_event obc.ping_requested

t=7
  expect scenario_status PASSED
```

The expected v0 projection is deliberately mixed.

### Projected

```text
scenario metadata
obc.ping command action
```

### Not projected

```text
initial mode
command_status ACCEPTED
obc.ping_requested event expectation
scenario_status PASSED
```

This proves that Stage 7.10 does not equate Core host-side expectations with
target verification observations.

## Deterministic atom decomposition

Atoms are emitted in semantic order independent of YAML mapping key order:

```text
scenario metadata
initial mode
initial telemetry sorted by Core ID
scenario steps in declared list order
within each step:
  command
  command arguments sorted by argument name
  telemetry injection
  event expectation
  mode expectation
  command expectation
  telemetry expectations sorted by Core ID
  nested documented expectations in fixed semantic order
```

Scenario step list order remains semantic.

Dictionary ordering is not used as hidden meaning.

## Command projection

A command with no arguments is projectable only when exactly one single-source
Profile binding matches:

```text
{domain: commands, id: <scenario command>}
```

and:

```text
binding.intent == project
```

The target action is resolved from Profile configuration:

```text
settings.pus.tc_apid
binding.config.pus.service
binding.config.pus.subtype
```

The resulting plan operation is:

```text
pus_tc
origin = profile_mapping
```

Profile `expected_responses` become:

```text
expect_pus_tm
origin = profile_expected_response
```

They do not become OrbitFabric scenario expectation atoms.

## Fail-closed command rules

### Arguments

Any non-empty scenario command `args` blocks the command in v0:

```text
OFI-VPROJ-CMDARGS-001
```

No argument payload is guessed.

### Missing binding

No matching single-source command binding:

```text
OFI-VPROJ-BINDING-001
```

### Explicit non-projection

A matching `do_not_project` binding:

```text
OFI-VPROJ-INTENT-001
```

### Ambiguous binding

More than one matching command binding:

```text
OFI-VPROJ-AMBIGUOUS-001
```

## Expectation handling

The documented v0 nested expectation keys are:

```text
command_status
payload_lifecycle
data_flow
scenario_status
```

All remain `not_projected`.

Existing top-level expectation forms also remain `not_projected`:

```text
expect_event
expect_mode
expect_command
expect_telemetry
```

Unknown nested expectation keys are not ignored.

They fail before plan publication:

```text
OFI-VPROJ-SCENARIO-002
```

An empty `expect` mapping also fails closed because it has no documented
semantic atom to record.

## Provenance

Every Core-entity-backed scenario atom is resolved through the consumed Core
Integration Input Set Entity Index.

Failure to resolve a scenario identity through the consumed input set is:

```text
OFI-VPROJ-PROVENANCE-001
```

The final plan is then passed through the Stage 7.10c provenance validator,
which checks:

```text
scenario SHA-256
Core input_set_sha256
Profile SHA-256
mission identity
OrbitFabric producer version
Profile binding source
PUS TC mapping
Profile expected_responses
```

## No OpenSVF dependency

The Stage 7.10d projector imports no `svf` module.

Its output boundary is the Verification Projection Plan.

The next stage may materialize that resolved plan into native OpenSVF assets,
but that is explicitly outside Stage 7.10d.

## Files

Stage 7.10d adds:

```text
docs/design/stage7_10d_verification_projector.md
integration_package/adapter/verification_projector.py
integration_package/tests/test_verification_projector.py
orbitfabric_models/scenarios/stage7_10_ping_verification.yaml
tools/validate_stage7_10d_verification_projector.py
```

No production modification is required in:

```text
OrbitFabric Core
OpenOBSW
OpenSVF
```

## Acceptance

Stage 7.10d is accepted when:

1. the PoC scenario validates through native OrbitFabric Core v1.2.0;
2. the scenario Mission Model identity matches the generated Core Integration
   Input Set;
3. existing target Profile compatibility preflight passes;
4. the reference scenario produces exactly six source atoms;
5. exactly two atoms are `projected`;
6. exactly four atoms are `not_projected`;
7. zero atoms are `blocked`;
8. the command atom resolves to Profile binding `cmd.ping`;
9. the command produces exactly one `pus_tc` operation;
10. that operation resolves to APID `0x010`, service `17`, subtype `1`;
11. Profile `expected_responses` produce exactly three `expect_pus_tm`
    operations in authored order;
12. command_status remains `not_projected`;
13. event expectation remains `not_projected`;
14. scenario_status remains `not_projected`;
15. scenario `t=5` remains provenance and creates no wait/schedule operation;
16. non-empty command arguments produce a blocked plan with
    `OFI-VPROJ-CMDARGS-001`;
17. unknown nested expectation semantics fail with
    `OFI-VPROJ-SCENARIO-002`;
18. repeated projection from identical inputs produces byte-identical plan
    output;
19. the projector imports no OpenSVF code;
20. OrbitFabric source working tree remains unchanged;
21. Stage 7.10d unit tests pass.
