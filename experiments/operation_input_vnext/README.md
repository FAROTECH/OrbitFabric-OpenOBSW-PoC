# Operation-Input vNext Pressure Test

Status: **Architecture Lab experiment — non-normative**

Branch:

```text
architecture/operation-input-vnext-pressure-test
```

Starting point:

```text
59a235b428a63449bbdb6a1b6c7acda582606090
```

which descends from the accepted Stage 7 v0 convergence baseline.

## Purpose

Pressure-test the smallest coherent operation-input contract evolution before any normative OrbitFabric contract is changed.

The candidate architecture under test is the current Architecture Lab shorthand:

```text
M1 + T1 + R1 + V1
```

but this first control slice intentionally exercises only the **version-lane and zero-additional-input behavior**.

## O4 control question

Can a new explicit package/protocol/Result lane execute the existing `project` operation naturally when that operation requires **no additional semantic inputs**?

The expected shape is:

```text
IISS + Profile
    |
    v
vNext project
    |
    v
Result inputs:
    core_input_set
    profile
    operation_inputs = []
```

No Scenario is involved in this slice.

## Disposable lab spellings

The following identifiers exist only to make the experimental lane unambiguous:

```text
manifest_version: 0.2-lab
protocol:         orbitfabric.adapter_cli.vnext-lab
result_version:   0.2-lab
adapter version:  0.2.0.dev1
```

They are **not proposed final OrbitFabric version identifiers**.

The provisional manifest field:

```text
input_requirements
```

is likewise test notation, not a promoted contract spelling.

For `project` this experiment declares:

```json
"input_requirements": []
```

## Explicitly not implemented yet

This control slice does not add:

```text
Scenario requirement
Scenario binding
--operation-input argv
operation-input cardinality rules
Scenario provenance
Scenario freshness
verification operation declaration
Studio vNext support
Core contract changes
```

Those are later pressure-test steps only if this zero-input control succeeds.

## Why project comes first

If vNext makes a project-only operation awkward, requires fake resources, or forces verification-specific concepts into the generic package boundary, the candidate is already over-shaped.

The control therefore establishes:

```text
new contract lane != mandatory extra input
```

before Scenario is introduced.

## Acceptance

O4 package-side acceptance requires:

```text
vNext manifest identity                                  PASS
project input_requirements = []                         PASS
installed package execution with IISS + Profile only    PASS
vNext Integration Result                                PASS
inputs.operation_inputs = []                            PASS
existing Stage 7 projection/artifact regressions        PASS
no new CLI argument required for project                PASS
```

Only after this is demonstrated should the Studio dual-lane consumer probe begin.
