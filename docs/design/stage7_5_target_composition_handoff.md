# Stage 7.5 — Target-owned SRDB composition handoff

Status: consolidated against merged upstream OpenOBSW baseline

## Purpose

Stage 7.4 established the static Adapter output boundary:

```text
OrbitFabric Core Integration Input Set
        +
Projection Profile
        ↓
OpenOBSW/OpenSVF Adapter
        ↓
mission_contract.h
obsw-srdb additive contribution bundle
integration_result.json
```

Stage 7.5 addresses the next downstream question:

> How can a generated additive contribution become part of a complete target SRDB without moving target composition semantics into the OrbitFabric Adapter?

## Ownership decision

Composition remains owned by `obsw-srdb`.

The reference chain is:

```text
Adapter-generated target-native contribution records
        ↓
SRDBContributionLoader
        ↓
SRDBComposer
        +
base complete SRDB
        ↓
complete validated SRDB
        ↓
obsw-srdb native C / XTCE codegen
```

The composition implementation is generic and contains no knowledge of:

```text
OrbitFabric Core
Projection Profiles
Integration Results
Studio
```

## Reference OpenOBSW baseline

The target-owned composition and external SRDB build-input capability is now merged upstream in OpenOBSW.

Canonical merged baseline:

lipofefeyt/openobsw
main: 44ceb71a016f0541ff7a0aa74191e13bafdb59c1

This merged baseline is now the canonical target reference for the downstream Stage 7 acceptance campaign.

It adds:

```text
SRDBContribution
SRDBContributionLoader
SRDBComposer
SRDBCompositionError
```

and target-side regression tests.

## Composition semantics

The first contract is additive-only.

The base spacecraft record remains authoritative.

Contributions may add:

```text
parameters
telecommands
hk_sets
events
```

No replacement or override semantics are provided.

Composition rejects collisions in target namespaces:

```text
Parameter.id
Parameter.name
Event.id
Event.name
HKSet.id
HKSet.name
Telecommand.name
Telecommand(apid, service, subservice)
```

After composition, HK parameter references must resolve against the complete composed parameter set.

## Separation from build-path selection

This slice deliberately does not modify OpenOBSW CMake.

These are separate concerns:

```text
composition
    -> how a complete valid SRDB is formed

build path selection
    -> which complete SRDB directory OpenOBSW build-time codegen consumes
```

A later increment may expose an external assembled SRDB path to CMake after the composition API itself is proven.

## PoC acceptance

The PoC-side acceptance harness is:

```text
tools/validate_stage7_5_target_composition.py
```

It consumes the real Stage 7.4 bundle and the exact OpenOBSW composition reference checkout, then proves:

```text
base SRDB loads through native SRDBLoader
Stage 7.4 contribution loads as target-native records
base + contribution composes without mutation/override
0x6001 telemetry parameter is present
SID 5 housekeeping set references that parameter
0x5001 MEDIUM event is present
TC(17,1) remains the single existing are_you_alive target
no synthetic obc_ping telecommand is created
native srdb_generated.h contains projected target records
native generated header compiles with strict C11
native XTCE codegen includes the projected telemetry/HK path
```

## Non-goals

Stage 7.5 does not yet add:

```text
OpenOBSW CMake external SRDB path selection
runtime execution
OpenSVF campaign execution
YAMCS orchestration
OrbitFabric adapter runtime capabilities
Core changes
Studio behavior
```

The purpose is to prove the target-owned application/composition boundary first.
