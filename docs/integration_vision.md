# OrbitFabric Core to OpenOBSW/OpenSVF Integration Vision

## Purpose

This document captures the intended direction for the integration between OrbitFabric Core and the OpenOBSW/OpenSVF ecosystem.

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

## Core Principle

OrbitFabric Core remains the semantic source of truth.

It owns mission-level definitions such as telemetry parameters, commands, events, faults, modes, packets, data products, and policies.

OpenOBSW/OpenSVF remain the execution and verification environment.

The integration layer translates OrbitFabric semantic mission definitions into concrete OpenOBSW/OpenSVF-facing artifacts.

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

## Target Continuity Chain

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

## Current Assessment of Development Effort

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

## The Missing Concept: Projection Profiles

One observation emerging from the PoC is that OrbitFabric currently models mission semantics well, while ecosystem-specific projection rules are still deliberately external.

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

For this PoC, the projection logic lives in the shared PoC repository.

Longer term, a reusable OpenOBSW/OpenSVF projection profile may live either on the OrbitFabric side or in a dedicated profile repository.

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
* OrbitFabric-side tooling or profile adapters can be responsible for producing projections.
* OpenOBSW/OpenSVF remain responsible for execution and verification.

## Potential Future Repository Structure

This is not an immediate PoC requirement.

A possible future OrbitFabric-side direction could be:

```text
orbitfabric/
├── core/
├── lint/
├── sim/
└── profiles/
     └── openobsw/
```

A cleaner option may be a dedicated repository:

```text
orbitfabric-openobsw-profile
```

containing:

```text
mapping logic
artifact generators
allocation rules
profile-specific validation
```

This would keep OrbitFabric Core independent from ecosystem-specific integrations.

For now, the shared PoC repository is the correct place for experimentation.

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

The goal is to establish a mission contract authority capable of projecting a validated mission definition into multiple engineering domains while preserving consistency, traceability, and verification continuity.

The success metric is not code generation.

The success metric is confidence that flight software, ground systems, verification activities, and operational evidence are all derived from the same mission truth.
