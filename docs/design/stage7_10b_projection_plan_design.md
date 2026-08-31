# Stage 7.10b: Verification Projection Plan Schema and Acceptance Matrix

## Purpose

Stage 7.10a froze the semantic boundary.

Stage 7.10b freezes the machine-readable handoff that sits between semantic
projection and OpenSVF materialization.

This slice still does not implement the projector.

The deliverables are:

```text
integration_package/schemas/verification-projection-plan-0.1.schema.json
integration_package/tests/stage7_10_projection_cases.json
docs/design/stage7_10b_projection_plan_design.md
```

## Contract rule

The plan is a PoC-owned Integration Package artifact.

It is not:

```text
a Core surface
a Mission Model replacement
an OpenSVF campaign
an OpenSVF evidence report
```

It records resolved verification projection decisions.

## Required invariants

### Exact accounting

```text
source_atoms
=
projected_atoms
+
not_projected_atoms
+
blocked_atoms
```

No source atom may disappear.

### Plan status

```text
blocked_atoms > 0
    -> status = blocked
```

`executable_subset` is allowed only when all operations selected by the v0
supported subset are resolved without semantic guessing.

`executable_subset` does not mean complete scenario equivalence.

### Provenance

The plan records exact SHA-256 provenance for:

```text
scenario bytes
Core Integration Input Set
Projection Profile bytes
```

It also records the OrbitFabric producer version, Profile identity/version,
integration identity/schema version, and adapter identity/version.

### Atom dispositions

Every atom has exactly one disposition:

```text
projected
not_projected
blocked
```

`not_projected` and `blocked` require a non-empty reason.

### Operation provenance

The first v0 operations are:

```text
pus_tc
expect_pus_tm
```

A `pus_tc` operation originates from:

```text
origin = profile_mapping
```

An `expect_pus_tm` operation originates from:

```text
origin = profile_expected_response
```

This prevents Profile target obligations from being mislabeled as OrbitFabric
scenario expectations.

### Scenario time

`scenario_t` is retained on atoms as source provenance.

The v0 plan defines no:

```text
wait
schedule_tc
PUS Service 11 scheduling
real-time delay
```

operation.

### Core command_status

The plan has no rule that maps:

```text
Core command_status: ACCEPTED
```

to:

```text
PUS TM(1,1)
```

The former is a Core host-side scenario expectation.

The latter is a Profile-authored target verification obligation.

## JSON Schema scope

JSON Schema validates structural properties such as:

```text
required fields
closed objects
enumerations
identifier shapes
SHA-256 shapes
PUS numeric ranges
disposition reason presence
operation-specific provenance
```

Cross-record semantic invariants are validator-owned, including:

```text
atom accounting reconciliation
unique atom IDs
unique operation IDs
operation ordering
atom -> operation reference integrity
binding resolution uniqueness
blocked count -> blocked status
projected command -> operation presence
Profile expected_response count -> target obligation count
exact hash verification against consumed files
byte-deterministic writing
```

These semantics must not be hidden in JSON Schema tricks.

## Diagnostic family

Stage 7.10b reserves the integration-owned projection diagnostic prefix:

```text
OFI-VPROJ-
```

Initial codes:

```text
OFI-VPROJ-CMDARGS-001
  command arguments require an explicit target encoder

OFI-VPROJ-BINDING-001
  selected source action has no executable Profile binding

OFI-VPROJ-INTENT-001
  selected source action is explicitly do_not_project

OFI-VPROJ-AMBIGUOUS-001
  more than one executable binding matches the selected source action

OFI-VPROJ-PLAN-001
  plan structural or semantic invariant failed

OFI-VPROJ-PROVENANCE-001
  exact consumed-input provenance does not match the plan
```

## Acceptance matrix

The machine-readable case file freezes at least these behaviors:

```text
VP-001 mapped ping positive path
VP-002 command_status non-equivalence
VP-003 scenario time provenance only
VP-004 command args fail closed
VP-005 missing Profile binding fail closed
VP-006 do_not_project fail closed
VP-007 initial state not projected
VP-008 telemetry expectation not projected
VP-009 event expectation not projected
VP-010 data-flow expectation not projected
VP-011 ambiguous bindings fail closed
VP-012 exact atom accounting
VP-013 blocked status invariant
VP-014 executable_subset claim boundary
VP-015 exact SHA-256 provenance
VP-016 byte-deterministic plan output
```

## First reference plan

For the first reference ping slice, the operations must resolve to:

```text
op-0001  pus_tc
         origin = profile_mapping
         binding = cmd.ping
         APID = 0x010
         service = 17
         subtype = 1

op-0002  expect_pus_tm
         origin = profile_expected_response
         binding = cmd.ping
         service = 1
         subtype = 1

op-0003  expect_pus_tm
         origin = profile_expected_response
         binding = cmd.ping
         service = 17
         subtype = 2

op-0004  expect_pus_tm
         origin = profile_expected_response
         binding = cmd.ping
         service = 1
         subtype = 7
```

All four operations reference the same source command atom for traceability, but
only the TC is the target representation of the source command action.

The three TM operations are target verification obligations supplied by the
Profile.

## Writer policy

The future writer must use the same deterministic style already used by the
PoC result writer:

```python
json.dumps(payload, indent=2, sort_keys=True) + "\n"
```

Repeated projection from byte-identical validated inputs must produce a
byte-identical plan.

## 7.10b acceptance

Stage 7.10b is frozen when:

1. the schema is valid Draft 2020-12;
2. it uses local references only;
3. objects are closed unless explicitly designed otherwise;
4. the positive reference-plan shape validates;
5. malformed operation provenance is schema-rejected;
6. the acceptance matrix contains VP-001 through VP-016;
7. the matrix distinguishes schema validation from semantic validator rules;
8. no projector implementation is introduced yet.
