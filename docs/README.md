# Documentation Map

This directory contains two different kinds of documentation:

1. **current baseline and architecture documents**, which describe how the repository should be interpreted now;
2. **historical Stage evidence**, which records what was known, pending, or intentionally out of scope at the time a specific engineering step was executed.

The distinction is important. A Stage 6 document may correctly say that a runtime path was still pending when that stage was written even though a later Stage closed it.

## Current baseline documents

Use these documents to understand the repository as it stands at the Reference Adapter `0.1.0` baseline:

- [`../README.md`](../README.md) - public repository overview and ownership boundary;
- [`reference_integration_baseline_v0_1.md`](reference_integration_baseline_v0_1.md) - frozen validation baseline;
- [`roadmap.md`](roadmap.md) - complete staged progression through Stage 7.10;
- [`integration_vision.md`](integration_vision.md) - current integration vision;
- [`mapping_concept.md`](mapping_concept.md) - current mapping and projection model;
- [`integration_responsibility_matrix.md`](integration_responsibility_matrix.md) - current ownership split;
- [`development_workflow.md`](development_workflow.md) - current contributor workflow;
- [`stage7_reference_integration_extraction.md`](stage7_reference_integration_extraction.md) - Stage 7 extraction history and closure.

## Supporting extraction/reference documents

- [`poc_asset_inventory.md`](poc_asset_inventory.md) - historical PoC asset classification with the current Reference Adapter interpretation layered on top.

These documents use a deliberately balanced viewpoint:

```text
producer semantics
        |
        v
integration boundary
        |
        v
downstream target/runtime semantics
```

No side of the integration is treated as an implementation detail of another.

## Historical evidence documents

The following families are historical engineering records:

```text
stage5_*
stage6_*
design/stage7_*
openobsw_* smoke / preparation documents
opensvf_* preparation / alignment documents
PoC pipeline evidence documents
```

Their stage-local status wording is intentionally preserved.

For example, a Stage 6.8 document may say that live YAMCS execution is pending because that statement was true at Stage 6.8. Later closure evidence does not make the historical document incorrect.

When historical wording conflicts with a later baseline statement, the later baseline document is authoritative for current repository status.

## Current scope

The current repository baseline covers:

```text
OrbitFabric Core Integration Input Set
+
Projection Profile
+
Reference Adapter 0.1.0
+
OpenOBSW / obsw-srdb target composition and runtime
+
OpenSVF runtime / campaign evidence
+
YAMCS representative runtime evidence
```

The repository does not define the final production packaging or repository topology.

The original PoC evidence and the Reference Adapter baseline remain valid even if future integration architecture work changes package discovery, orchestration, contract versions, or repository placement.
