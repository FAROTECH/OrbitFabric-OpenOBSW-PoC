# OrbitFabric <-> OpenOBSW/OpenSVF Integration Vision

## Purpose

This document captures the intended direction for the integration boundary between OrbitFabric Core and the OpenOBSW/OpenSVF ecosystem.

The objective is not to turn OrbitFabric into a flight software framework, nor to replace OpenOBSW, OpenSVF, XTCE, YAMCS, or existing PUS tooling.

The objective is to establish a model-driven continuity chain between:

```text
Mission definition
-> flight software contracts
-> ground database artifacts
-> verification campaigns
-> operational evidence
```

The first proof of concept is intentionally small.

Its purpose is to prove the integration boundary, not to cover a complete spacecraft mission.

## Current Baseline Update

The original PoC is now closed through Stage 6.20, and the first Reference Integration extraction is validated through Stage 7.10.

```text
producer side
    OrbitFabric Core Integration Input Set

integration boundary
    Projection Profile
    Integration Package / Adapter
    Integration Result

downstream side
    obsw-srdb target composition
    OpenOBSW flight/runtime behavior
    OpenSVF simulation/campaign/YamcsBridge behavior
    YAMCS ground-runtime behavior
```

The reference Adapter implementation is frozen at `0.1.0`.

The generic Projection Profile, Integration Package, and Integration Result contracts remain `0.1-candidate`.

This is a validated reference baseline, not a declaration that future package topology or generic integration architecture is permanently complete.


## Ownership Principle

OrbitFabric Core remains the semantic source of truth.

It owns mission-level definitions such as telemetry parameters, commands, events, faults, modes, packets, data products, and policies.

OpenOBSW and `obsw-srdb` retain target-composition and flight/runtime authority.

OpenSVF retains simulation, campaign, procedure, bridge, and verification semantics, while YAMCS retains ground-runtime semantics.

The integration layer connects the Core-owned semantic input to those downstream-owned target/runtime contracts through explicit projection, validation, traceability, and provenance.

## Key Architectural Boundary

OrbitFabric Core should not own transport-specific or implementation-specific numeric allocations as stable mission truth.

Example semantic identifiers:

```text
eps.obc.bus_voltage_mv
obc.ping
eps.voltage_out_of_bounds
```

may be projected by the PoC adapter into concrete integration identifiers such as:

```text
OF_TM_OBC_BUS_VOLTAGE_MV = 0x4001
OF_CMD_PING = 0x1701
OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001
```

Numeric values belong to the integration/profile layer, not to the Core semantic model.

## Original PoC Continuity Chain (Historical)

```text
OrbitFabric Mission Model
    ↓
OrbitFabric validation/lint
    ↓
OpenOBSW/OpenSVF adapter profile
    ↓
Generated flight software contract
    ↓
Generated ground segment database artifact
    ↓
Generated or assisted verification campaign
    ↓
OpenOBSW/OpenSVF execution
    ↓
YAMCS visibility
    ↓
Verification evidence
```

This original PoC chain remains useful as historical context. The current Stage 7 boundary refines it through the Core Integration Input Set, Projection Profile, Adapter, target-owned SRDB composition, and Integration Result described above.

The important point is that telemetry, commands, events, faults, packets, and verification expectations should not be manually redefined at each layer.

## Why This Integration Is Interesting

The immediate outcome of the PoC is intentionally modest:

```text
Mission Model
-> mission_contract.h
-> SRDB YAML
-> XTCE
-> YAMCS
```

By itself, this is useful but not the core value.

The potentially interesting aspect lies elsewhere.

The long-term value comes from preserving the same mission definition across multiple engineering domains without repeatedly redefining the same information.

Spacecraft projects often contain independent representations of the same concepts:

```text
system engineering documents
flight software definitions
ground database definitions
XTCE models
test procedures
verification scripts
operations documentation
```

Each representation can evolve independently.

The result is duplicated effort, integration friction, and configuration drift.

If this direction proves practical, the value does not come from artifact generation alone.

The value comes from preserving consistency across the lifecycle.

## Early PoC Assessment of Development Effort (Historical)

Current working assessment for the initial PoC:

```text
OrbitFabric Core evolution          Low to Medium
OpenOBSW/OpenSVF adapter layer      High
OpenSVF/OpenOBSW core modifications Low to Medium
```

OpenOBSW and OpenSVF already possess mature concepts for:

```text
PUS services
telemetry handling
verification workflows
SRDB structures
XTCE generation
YAMCS integration
```

The integration does not require replacing those capabilities.

Instead, it requires feeding them with information derived from a higher-level mission definition.

Some OpenSVF/OpenOBSW adjustments may still be needed around SRDB ingestion, generated artifact placement, or test harness integration. Those changes should remain minimal and justified by the PoC.

## Projection Profiles: From PoC Observation to Reference Baseline

An early PoC observation was that mission semantics and ecosystem-specific projection rules needed an explicit boundary.

Stage 7 has now turned that observation into a version-controlled Projection Profile consumed by the Reference Adapter.

Conceptually:

```text
Mission Model
    ↓
Projection Profile
    ↓
Generated Artifacts
```

Examples:

```text
Mission Model
    ↓
OpenOBSW/OpenSVF Profile
    ↓
mission_contract.h
SRDB YAML

Mission Model
    ↓
Future OpenC3 Profile

Mission Model
    ↓
Future cFS Profile
```

The Mission Model remains stable.

Profiles determine how that model is projected into a specific ecosystem.

For the current Reference Integration, the Projection Profile and Adapter implementation live in this shared repository.

Longer term, production packaging may remain here or move to a dedicated Adapter/profile repository. That repository-topology decision remains open and does not change the validated ownership boundary.

## Adapter Ownership

For the PoC, adapter ownership is shared through this repository.

The architectural preference is:

```text
OrbitFabric Mission Model
    ↓
PoC OpenOBSW/OpenSVF adapter profile
    ↓
Generated artifacts
    ↓
OpenOBSW/OpenSVF
```

rather than:

```text
OpenSVF or OpenOBSW directly depending on OrbitFabric internals
```

Reasoning:

* OpenOBSW/OpenSVF should remain independent consumers.
* They should not need to understand OrbitFabric internals.
* They should continue consuming standard or ecosystem-native artifacts such as C headers, SRDB YAML, and XTCE-compatible inputs.
* The shared Integration Adapter can be responsible for producing explicit target projections.
* OpenOBSW/OpenSVF remain responsible for execution and verification.

## Potential Future Repository Structure

The current repository is both historical PoC evidence and the incubation location of the first Reference Adapter.

A future productionization step may extract the durable integration into a dedicated package or repository, for example:

```text
orbitfabric-openobsw-adapter
```

or another topology chosen after the generic Integration Package lifecycle is clearer.

The important architectural constraint is not the repository name. It is that Core remains backend-agnostic, the Adapter remains at the integration boundary, and downstream target/runtime semantics remain owned by OpenOBSW/obsw-srdb/OpenSVF/YAMCS.

## Semantic Events vs Physical PUS Events

Not every OrbitFabric event should necessarily become a physical PUS Service 5 event.

Example:

```text
obc.ping_requested
```

may remain a semantic Core event.

The PUS layer already provides:

```text
TM[1,1] acceptance success
TM[1,7] completion success
TM[17,2] connection test report
```

Generating an additional TM[5,1] event for every ping would likely be redundant and could pollute the operational event stream.

Therefore:

```text
Core semantic event:
  obc.ping_requested
  -> no physical TM[5,x] for the first PoC

Operational warning event:
  eps.voltage_out_of_bounds
  -> physical TM[5,3]
```

The adapter should preserve meaning, not blindly materialize every semantic concept on the wire.

## Long-Term Observation

The most valuable future outcome may not be generated code, XTCE, or SRDB files.

The potentially more interesting outcome is:

```text
telemetry defined once
command defined once
event defined once
fault defined once
```

and then reused consistently across:

```text
flight software
ground segment
verification
operations
```

If achieved, this would provide a continuous and traceable path from mission definition to operational evidence.

That is still relatively uncommon across many CubeSat and small satellite development workflows.

## Final Thought

The goal is not to create another flight software framework.

The goal is to establish an explicit integration contract boundary that connects a validated mission definition to downstream target, runtime, and verification domains while preserving consistency, ownership, traceability, and evidence continuity.

The success metric is not code generation.

The success metric is confidence that flight software, ground systems, verification activities, and operational evidence are all derived from the same mission truth.
