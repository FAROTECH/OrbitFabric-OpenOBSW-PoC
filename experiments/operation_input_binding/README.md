# Operation Input Binding Pressure Test

Status: **Architecture Lab experiment — non-normative**

This directory exists only on the experimental branch:

```text
architecture/operation-input-binding-pressure-test
```

It pressure-tests one question derived from the private OrbitFabric Architecture Lab:

> Can the existing Stage 7.10 verification projection path accept one explicit Core-owned Scenario as an additional operation input while leaving the current mission-level Core Integration Input Set and Projection Profile boundaries intact?

## What this experiment is

The probe exercises:

```text
explicit Scenario file binding
        +
Core Integration Input Set
        +
Projection Profile
        |
        v
existing Stage 7.10 verification projector
        |
        v
validated Verification Projection Plan
        |
        v
existing OpenSVF materializer
        |
        v
machine-readable probe provenance
```

The probe output is:

```text
operation_input_binding_probe.json
```

It records:

```text
working operation-input declaration
local Scenario binding
resolved Scenario id + exact SHA-256
IISS provenance
Profile provenance
projection accounting
plan digest
materialization manifest digest
operation trace
```

## What this experiment is not

It is **not**:

```text
orbitfabric.adapter_cli.v1
a modification of orbitfabric.adapter_cli.v0
a generic Integration Result revision
a generic Scenario Integration Surface
a generic Scenario Atom contract
a generic verification-operation vocabulary
a Studio implementation
a native OpenSVF execution result
```

No current OrbitFabric contract is promoted or changed by this branch.

## Semantic ownership

The probe does not parse or reinterpret Scenario semantics.

It delegates to the existing Stage 7.10 projector, which uses OrbitFabric Core `ScenarioLoader` and validates Scenario / Core Integration Input Set mission coherence.

The existing OpenSVF materializer consumes only the validated projection plan and does not reread the Scenario.

Therefore the intended ownership remains:

```text
OrbitFabric Core
    Scenario semantics / validation

Integration Package
    target projection

OpenSVF materializer
    mechanical native asset generation
```

## Reference inputs

The Stage 7.10 reference slice is expected to use:

```text
Scenario
    orbitfabric_models/scenarios/stage7_10_ping_verification.yaml

Projection Profile
    projection_profiles/poc_openobsw_opensvf.yaml

OpenSVF spacecraft template
    execution/opensvf/stage7_10_spacecraft.yaml

Core Integration Input Set
    generated from orbitfabric_models/mission using the pinned Core baseline
```

## Example

After producing a coherent Core Integration Input Set with the pinned OrbitFabric Core:

```bash
python experiments/operation_input_binding/probe.py \
  --scenario orbitfabric_models/scenarios/stage7_10_ping_verification.yaml \
  --input-set-manifest <generated>/integration_input_manifest.json \
  --profile projection_profiles/poc_openobsw_opensvf.yaml \
  --spacecraft execution/opensvf/stage7_10_spacecraft.yaml \
  --output-dir <probe-output>
```

## Acceptance for this probe

The host-side probe passes when:

```text
Scenario is consumed explicitly
Scenario semantic validation remains Core-backed
Scenario/IISS mission coherence passes
projection plan is executable_subset
source atom accounting reconciles
the expected resolved operations are retained
OpenSVF assets materialize from the plan only
probe provenance contains exact Scenario/IISS/Profile digests
Scenario remains outside mission-level IISS
```

Native CampaignRunner execution remains separately evidenced by Stage 7.10f and is deliberately not duplicated here.
