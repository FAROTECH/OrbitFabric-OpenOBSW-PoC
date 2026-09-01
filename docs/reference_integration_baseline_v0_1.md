# OrbitFabric OpenOBSW/OpenSVF Reference Integration Baseline v0.1

Status: **validated reference baseline**

Baseline date: **2026-09-01**

## 1. Purpose

This document records the first frozen validation baseline of the OrbitFabric OpenOBSW/OpenSVF Reference Integration.

It is intended to provide a stable engineering reference point after completion of the original thin PoC and the subsequent Stage 7 extraction work.

The baseline establishes what has been demonstrated and what the current Adapter implementation exposes.

It does not declare the producer/integration/downstream architecture permanently complete.

## 2. Baseline identity

Reference integration:

```text
orbitfabric-openobsw-opensvf
```

Reference Adapter:

```text
version: 0.1.0
protocol: orbitfabric.adapter_cli.v0
```

Current public Adapter operation:

```text
project
```

Advertised capabilities:

```text
profile_validation
projection
artifact_generation
traceability
```

The Adapter implementation version is frozen at `0.1.0` for this reference baseline.

The surrounding generic external contracts remain independently versioned candidate surfaces:

```text
Integration Package contract
    0.1-candidate

Projection Profile contract/schema
    0.1-candidate

Integration Result contract
    0.1-candidate
```

Adapter `0.1.0` therefore identifies a validated reference implementation baseline. It does not implicitly promote those generic contracts to stable `1.0` or equivalent status.

## 3. Pinned reference baselines

The Stage 7.10 final runtime acceptance used:

```text
OrbitFabric Core
b1aa95408710f697b0ee144a7b41f2376395e01f
v1.2.0

OpenOBSW
44ceb71a016f0541ff7a0aa74191e13bafdb59c1

OpenSVF
667d3eadcb0bbd7814ac324b99946c4ed2f11f23
```

The Stage 7.10 implementation was merged into the PoC/reference repository through PR #39:

```text
merge commit
e253d2a51b9c10ec8244a494700fb1df8d2183b9
```

These commits identify the producer and downstream baselines against which the final dual-branch runtime evidence was established.

## 4. Validated integration chain

The baseline establishes the following durable chain:

```text
OrbitFabric Mission Model
        |
        v
Core Integration Input Set
        |
        v
Projection Profile
        |
        v
Integration Package / Adapter
        |
        +-> OpenOBSW-facing contract
        |
        +-> obsw-srdb contribution
        |
        +-> Integration Result
        |
        v
target-owned composition
        |
        v
OpenOBSW build/runtime
        |
        v
OpenSVF runtime / campaign
        |
        v
machine-readable evidence
```

The same authoritative Core Integration Input Set and Projection Profile were also exercised through the Stage 7.10 verification branch:

```text
Core Integration Input Set
        +
Projection Profile
        +
OrbitFabric scenario
        |
        v
Verification Projection Plan
        |
        v
OpenSVF procedure materialization
        |
        v
OpenOBSW runtime built from the projected contract and composed target SRDB
        |
        v
native OpenSVF CampaignReport
```

## 5. Original PoC evidence baseline

The original thin PoC objective was completed before the Stage 7 extraction.

Representative end-to-end evidence includes:

```text
Telemetry

eps.obc.bus_voltage_mv
-> OpenOBSW TM(3,25)
-> OpenSVF YamcsBridge
-> YAMCS archive / MDB classification
```

```text
Command

YAMCS TC(17,1)
-> OpenSVF YamcsBridge
-> OBCEmulatorAdapter
-> OpenOBSW
-> TM(1,1), TM(17,2), TM(1,7)
-> YAMCS
```

```text
Event

eps.voltage_out_of_bounds
-> OpenOBSW TM(5,3)
-> OpenSVF YamcsBridge
-> YAMCS archive / MDB classification
```

The PoC evidence remains useful as historical evidence and regression material.

## 6. Stage 7 extraction baseline

Stage 7 converted the proven PoC path into an explicit reference integration boundary.

The baseline includes:

```text
Core Integration Input Set consumption
version-controlled Projection Profile
package-published Profile schema
static Integration Package manifest
out-of-process adapter_cli.v0
project operation
compatibility preflight
deterministic artifact generation
Integration Result
traceability
provenance
target-owned SRDB composition
native OpenOBSW build/runtime consumption
native OpenSVF runtime consumption
native campaign evidence
explicit verification-projection reference path
```

The public `0.1.0` Adapter surface intentionally remains centered on the `project` operation.

## 7. Verification projection status

Stage 7.10 established that OrbitFabric scenario intent can be projected into target verification behavior without collapsing semantic ownership boundaries.

The reference implementation distinguishes:

```text
OrbitFabric host-side scenario semantics
!=
target Profile obligations
!=
OpenSVF verification semantics
!=
OpenOBSW runtime evidence
```

For example:

```text
OrbitFabric command_status: ACCEPTED
!=
PUS TM(1,1)
```

PUS response expectations are projected from explicit Profile obligations, not inferred from the OrbitFabric host-side expectation.

Likewise:

```text
scenario t
=
provenance
```

and is not silently converted into runtime scheduling.

Verification projection is fully implemented and runtime-validated as a reference extension, but it is not advertised as a first-class operation in the Adapter `0.1.0` public package surface.

Promoting it into the public package surface remains a future productization decision.

## 8. Explicit semantic and ownership boundaries

### Core semantic identity vs target allocation

OrbitFabric Core owns semantic mission identity.

Numeric IDs, PUS mappings, APIDs, SIDs, SRDB names, and similar target allocations are integration or Projection Profile concerns unless a future contract explicitly states otherwise.

Therefore:

```text
OrbitFabric semantic identity
!=
target numeric allocation
```

### C contract representation vs binary wire layout

The generated C contract representation is not implicitly a normative wire-format contract.

Therefore:

```text
generated C struct
!=
guaranteed serialized packet layout
```

Packing, alignment, byte ordering, explicit padding, and target serialization remain target/integration responsibilities unless a generated artifact explicitly claims binary-layout authority.

A consumer must not infer that an in-memory C structure is safe for direct packet `memcpy` solely because it was generated from the OrbitFabric contract.

### Compatibility labels vs compatibility enforcement

A version string by itself is not treated as proof of compatibility.

The Stage 7 boundary uses explicit compatibility validation and provenance, including:

```text
Core producer/version checks
Input Set identity and digests
Profile/schema validation
target baseline validation
resolved compatibility facts
Integration Result provenance
```

## 9. Integration Result role

The Integration Result remains the Adapter-produced, machine-readable record of one integration operation.

It records the relationship between:

```text
Core Integration Input Set
Projection Profile
Adapter identity/version
resolved target compatibility
generated artifacts
mapping/traceability
diagnostics
coverage
provenance
```

The generic Integration Result contract remains `0.1-candidate`.

Adapter `0.1.0` does not change that contract status.

## 10. Stage 7.10 maintenance watchpoint

The Stage 7.10 implementation contains an explicit v0 scenario-expectation vocabulary represented by:

```text
KNOWN_EXPECT_KEYS
NOT_PROJECTED_REASONS
```

These are intentionally visible boundaries.

As OrbitFabric scenario semantics evolve, these are among the first integration points that must be reviewed so that new expectation semantics are never silently ignored or incorrectly projected.

Unknown expectation semantics remain fail-closed.

This is a maintenance boundary, not a blocker to the current baseline.

## 11. What this baseline does not claim

This baseline does not claim:

```text
production mission integration
flight-qualified software
hardware-target validation
HIL validation
production FDIR
production commanding security / authorization
stable generic Adapter discovery / installation
stable generic Integration Package lifecycle
stable verification operation API
generic requirement projection
complete OrbitFabric scenario projection coverage
normative binary wire-layout generation
final numeric allocation namespace policy
final repository/package topology
```

These are separate productionization or architecture workstreams.

## 12. Repository role after the baseline

This repository originated as a PoC workspace and subsequently became the incubation location for the first durable OpenOBSW/OpenSVF Reference Integration.

At this baseline it therefore contains three kinds of valuable material:

```text
historical PoC evidence
+
validated Reference Integration implementation
+
productionization / extraction incubation material
```

The repository name does not imply that the final production Adapter must permanently remain here.

A future architecture decision may extract the durable Adapter into a dedicated repository or package while preserving this repository as reference evidence and regression material.

Such extraction would be an evolution of packaging and ownership topology, not a retroactive invalidation of the `0.1.0` baseline.

## 13. Future evolution

Likely follow-up areas include:

```text
dedicated Adapter repository/package extraction
generic Adapter discovery and installation
operation-input and orchestration evolution
Integration Package contract evolution
verification projection productization
requirement projection
binary-layout contracts where explicitly required
target allocation / namespace policy
additional verification semantics
additional downstream adapters
hardware / HIL validation
```

These items should be treated as explicit new workstreams rather than indefinite continuation of the original PoC.

## 14. Baseline interpretation

The intended interpretation of this milestone is:

```text
PoC evidence baseline
    achieved

Reference Integration extraction
    achieved

Reference Adapter implementation
    frozen at 0.1.0

generic integration architecture
    still evolvable

productionization
    future work
```

In short:

> The original OrbitFabric/OpenOBSW/OpenSVF PoC has reached its validated evidence baseline, and the first Reference Integration Adapter baseline is frozen as v0.1.0. This closes the current PoC-to-reference-integration extraction cycle, not the evolution of the integration architecture.
