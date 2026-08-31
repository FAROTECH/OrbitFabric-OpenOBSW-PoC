# Stage 7.10c: Verification Projection Plan Validator

## Objective

Stage 7.10c implements validation of the Stage 7.10b Verification Projection
Plan contract before any projector exists.

This slice intentionally validates plans that are manually constructed by tests
and acceptance fixtures.

It does not derive a plan from an OrbitFabric scenario.

## Responsibility

The validator owns three layers.

### 1. Structural validation

The committed Draft 2020-12 JSON Schema owns:

```text
closed object shapes
required fields
enum values
identifier patterns
SHA-256 textual shape
PUS numeric ranges
operation-specific origin tokens
reason presence for not_projected / blocked atoms
```

### 2. Cross-record semantic validation

`integration_package.adapter.verification_plan` owns invariants that are clearer
and safer in code than in JSON Schema:

```text
unique atom IDs
unique operation IDs
contiguous operation ordering
exact atom accounting
exact action / expectation accounting
exact Profile obligation accounting
blocked atom -> blocked plan status
no blocked atom -> executable_subset status
atom -> operation reference integrity
operation -> atom back-reference integrity
atom / operation binding integrity
non-projected atoms own no executable operations
projected command owns exactly one PUS TC
projected Core expectation atoms remain forbidden in v0
scenario metadata remains provenance-only
```

### 3. Consumed-input provenance validation

Given the actual consumed scenario path, loaded Core Integration Input Set and
loaded Projection Profile, the validator checks:

```text
scenario byte SHA-256
Core input_set_sha256
Core mission identity
Core model version
OrbitFabric producer version
Profile kind
Profile contract version
Profile id
Profile authored version
Profile byte SHA-256
```

For every projected command atom it also verifies:

```text
atom source == Profile binding source
binding intent == project
resolved PUS TC == Profile PUS mapping
resolved target TM obligations == Profile expected_responses
```

This is the critical boundary that keeps Profile-authored verification
obligations distinct from OrbitFabric-authored scenario expectations.

## No projector in this slice

Stage 7.10c does not decide:

```text
which scenario atom should be projected
which unsupported atom should be not_projected
which unresolved atom should be blocked
how scenario YAML is decomposed into atoms
```

Those decisions belong to the later projector.

Stage 7.10c only verifies that an already-produced plan is internally coherent
and faithful to the consumed inputs it claims.

## Deterministic writer

The module also defines the only allowed v0 plan serialization:

```python
json.dumps(payload, indent=2, sort_keys=True) + "\n"
```

The writer validates before writing.

Byte-identical validated payloads therefore produce byte-identical plan files.

This is serialization behavior, not projection behavior.

## Diagnostics

Structural and cross-record plan failures use:

```text
OFI-VPROJ-PLAN-001
phase = verification_projection
owner = integration
```

Consumed-input provenance or Profile-resolution mismatch uses:

```text
OFI-VPROJ-PROVENANCE-001
phase = verification_projection
owner = integration
```

Projector-specific diagnostics already frozen in Stage 7.10b remain reserved
for the later projector:

```text
OFI-VPROJ-CMDARGS-001
OFI-VPROJ-BINDING-001
OFI-VPROJ-INTENT-001
OFI-VPROJ-AMBIGUOUS-001
```

The validator must not manufacture those diagnostics because it does not make
projection decisions.

## Files

Stage 7.10c adds:

```text
integration_package/adapter/verification_plan.py
integration_package/tests/test_verification_projection_plan.py
tools/validate_stage7_10c_projection_plan_contract.py
docs/design/stage7_10c_projection_plan_validator.md
```

It does not modify:

```text
OrbitFabric Core
OpenOBSW
OpenSVF
Projection Profile
Stage 7.10b schema
Stage 7.10b acceptance matrix
```

## Acceptance

Stage 7.10c is accepted when:

1. the committed Stage 7.10b schema validates the reference plan;
2. cross-record accounting is recomputed rather than trusted;
3. duplicate IDs are rejected;
4. operation ordering is enforced;
5. atom/operation references are bidirectionally consistent;
6. atom/operation Profile binding identity is consistent;
7. projected command atoms own exactly one PUS TC;
8. projected Core expectation atoms remain rejected in v0;
9. exact scenario/Core/Profile provenance is verified;
10. the PUS TC resolution is checked against the consumed Profile;
11. the target TM obligations are checked exactly against Profile
    `expected_responses`;
12. deterministic writer output is byte-stable;
13. VP-001 through VP-016 remain present;
14. unit tests pass;
15. no projector or OpenSVF materializer is introduced.
