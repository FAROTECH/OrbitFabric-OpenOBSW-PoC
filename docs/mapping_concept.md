# OrbitFabric ↔ OpenOBSW / OpenSVF Integration Concept & Mapping

## 1. Introduction and Scope

This document defines the conceptual mapping and integration boundary between OrbitFabric Core and the OpenOBSW/OpenSVF execution stack.

The PoC demonstrates a thin vertical slice of an MBSE workflow:

```text
OrbitFabric Core Mission Model
-> OrbitFabric lint validation
-> PoC adapter / mapping layer
-> generated flight-side contract
-> generated ground-side database artifact
-> OpenOBSW execution
-> OpenSVF/YAMCS validation and visibility
```

The PoC is intentionally narrow. It is meant to prove the contract continuity chain, not to model a complete spacecraft mission.

## 2. Architectural Boundary

OrbitFabric Core remains the semantic Mission Data Contract authority.

OrbitFabric Core owns mission-level concepts such as:

* telemetry parameters;
* commands;
* events;
* faults;
* modes;
* packets;
* data products;
* policies.

OpenOBSW and OpenSVF remain execution and verification environments.

The PoC adapter consumes:

```text
orbitfabric_models/mission/
orbitfabric_models/poc_slice.yaml
```

and generates ecosystem-facing artifacts.

OrbitFabric Core itself does not become dependent on OpenOBSW, OpenSVF, YAMCS, XTCE, or PUS-specific tooling.

## 3. Source Model vs PoC Mapping Layer

The PoC uses two distinct inputs.

### 3.1 OrbitFabric Core Mission Model

```text
orbitfabric_models/mission/
```

This is the semantic source model validated by OrbitFabric Core.

It contains the OrbitFabric-compatible mission YAML files:

* `spacecraft.yaml`
* `subsystems.yaml`
* `modes.yaml`
* `telemetry.yaml`
* `commands.yaml`
* `events.yaml`
* `faults.yaml`
* `packets.yaml`
* `policies.yaml`

Validation command:

```bash
orbitfabric lint orbitfabric_models/mission/
```

### 3.2 PoC Mapping / Allocation Layer

```text
orbitfabric_models/poc_slice.yaml
```

This file is PoC-specific.

It maps the semantic OrbitFabric model to integration-specific details, including:

* `OF_` C identifiers;
* provisional numeric allocation values;
* SRDB canonical names;
* PUS service/subservice mapping;
* housekeeping set metadata.

Numeric values such as:

```text
0x4001
0x1701
0x5001
```

are PoC adapter allocation values.

They are not OrbitFabric Core-stable semantic identifiers.

They are also not APIDs, packet IDs, or packed PUS service/subservice identifiers. For example, `0x1701` is mnemonic for the PoC ping allocation but must not be interpreted as the wire encoding of `TC[17,1]`. PUS alignment is defined only by the explicit mapping fields such as `pus_service`, `pus_subtype`, housekeeping SID, and event mapping.

## 4. High-Level Data Flow

1. **Mission Definition**

   Mission semantics are defined in `orbitfabric_models/mission/`.

2. **Validation**

   The Mission Model is validated with OrbitFabric Core.

3. **Artifact Generation via PoC Adapter**

   The adapter consumes the validated Mission Model and the PoC mapping/allocation file.

   Flight side:

   ```text
   generated_artifacts/flight_software/mission_contract.h
   ```

   The generated flight-side contract header is an in-memory contract boundary. Structs such as `of_hk_obc_t` describe the semantic C representation expected by the adapter boundary. They are not wire-format payload definitions and must not be copied directly into PUS telemetry with `memcpy`.

   Wire serialization, including byte order for multi-byte fields and any packing/alignment constraints, belongs to the OpenOBSW/PUS adapter layer.

   Ground side:

   ```text
   generated_artifacts/ground_segment/poc_srdb.yaml
   ```

4. **OpenSVF/YAMCS Database Generation**

   OpenSVF remains responsible for generating or assisting the XTCE/YAMCS MDB from OpenSVF-compatible SRDB input.

   The current PoC baseline uses a PoC-side wrapper to load the generated SRDB through OpenSVF and write a local generated MDB artifact under `execution/generated/`.

5. **OpenOBSW Execution**

   OpenOBSW consumes the flight-side contract and runs the contracted command, telemetry, and event behavior.

6. **Validation and Evidence**

   OpenSVF/YAMCS validate command execution, telemetry visibility, and event/alarm behavior.

   The current runtime evidence baseline validates the PUS ping command path through OpenSVF pipe mode and the OrbitFabric-enabled OpenOBSW host simulator.

## 5. Conceptual Mapping Dictionary

| OrbitFabric Concept | OpenOBSW Flight Stack | OpenSVF / YAMCS Ground Segment | PUS-C Mapping |
| :--- | :--- | :--- | :--- |
| Telemetry Parameter | Struct member or registered HK parameter | SRDB parameter / XTCE parameter | Service 3 housekeeping |
| Command | TC dispatch target | XTCE MetaCommand / command path | Service 17 for ping, Service 8 for future function management |
| Event / Fault | Event trigger or FDIR condition | YAMCS event/alarm visibility | Service 5 event reporting when physically materialized |
| Packet | HK set or payload shape | XTCE SequenceContainer | Service 3 packet/report structure |
| Mode / State | OpenOBSW FSM/context | YAMCS system variable or event stream | Mission-specific |

## 6. Thin Vertical Slice Definition

The initial slice contains:

### 6.1 Telemetry

OrbitFabric semantic ID:

```text
eps.obc.bus_voltage_mv
```

PoC contract name:

```text
obc_bus_voltage_mv
```

Type:

```text
uint16 / uint16_t
```

Meaning:

```text
Raw millivolts
```

Behavior:

```text
Sampled at 1 Hz and carried in the `obc_hk` housekeeping packet.
```

PUS target:

```text
TM[3,25] housekeeping report
```

SRDB canonical name:

```text
eps.obc.bus_voltage_mv
```

### 6.2 Command

OrbitFabric semantic ID:

```text
obc.ping
```

PoC contract name:

```text
ping
```

PUS target:

```text
TC[17,1] connection test
```

Expected OpenOBSW response chain:

```text
TM[1,1] acceptance
TM[17,2] connection test response
TM[1,7] execution completion
```

### 6.3 Event / Fault

OrbitFabric semantic event:

```text
eps.voltage_out_of_bounds
```

Fault condition:

```text
eps.obc.bus_voltage_mv > 3500
```

PUS target:

```text
TM[5,3] warning event
```

SRDB canonical name:

```text
eps.obc.voltage_out_of_bounds
```

## 7. Semantic Events vs Physical PUS Events

Not every OrbitFabric event should automatically become a physical PUS Service 5 event.

Example:

```text
obc.ping_requested
```

can remain a semantic event inside the OrbitFabric model.

The PUS command path already provides:

```text
TM[1,1] acceptance
TM[1,7] completion
TM[17,2] connection test response
```

Generating an additional physical TM[5,x] event for every ping would be redundant for this PoC.

By contrast:

```text
eps.voltage_out_of_bounds
```

has operational meaning and can be materialized as a PUS Service 5 warning event.

The adapter should preserve meaning. It should not blindly materialize every semantic concept onto the wire.

## 8. Validated Baseline After Stage 6.3

The following parts of the mapping chain are validated in the current repository baseline:

```text
OrbitFabric Core-compatible Mission Model
-> PoC mapping/allocation layer
-> generated mission_contract.h
-> generated OpenSVF-compatible SRDB YAML
-> local OpenSVF XTCE/MDB generation wrapper
-> OpenSVF campaign runner
-> SpacecraftLoader
-> OBCEmulatorAdapter
-> pipe mode
-> OrbitFabric-enabled OpenOBSW obsw_sim
-> TC(17,1)
-> TM(1,1), TM(17,2), TM(1,7)
```

The Stage 6.3 runtime smoke validates the first command loop.

It does not validate yet:

```text
TM(3,25) housekeeping telemetry runtime visibility
TM(5,3) event/fault runtime visibility
YAMCS runtime execution
SRDB version-handshake packaging
```

The important runtime rule discovered in Stage 6.3 is:

```yaml
simulation:
  realtime: true
```

Campaign procedures that observe telemetry in wall-clock time should use realtime simulation mode.

## 9. Settled Decisions

| Decision | Resolution |
| :--- | :--- |
| OrbitFabric entry point | OrbitFabric Core |
| Studio dependency | Not part of the PoC pipeline |
| Core role | Semantic Mission Data Contract authority |
| Adapter role | Projection/mapping layer from Core model to ecosystem artifacts |
| `mission_contract.h` role | Contract-only C11 header |
| C prefix | `OF_` |
| Numeric IDs | PoC adapter allocation values, not APIDs, packet IDs, or packed PUS service/subservice identifiers |
| HK C structs | In-memory contract representations, not wire-format payload layouts |
| Ground artifact path | PoC adapter -> OpenSVF-compatible SRDB -> OpenSVF XTCE/YAMCS MDB |
| First execution target | OpenOBSW host simulation through OpenSVF pipe mode |
| Custom bridge process | Not needed for the first runtime smoke |
| STM32/bare-metal | Deferred until the contract boundary is stable |

## 10. Current Open Items

1. Keep top-level documentation synchronized with the actual merged PoC baseline.
2. Validate the runtime housekeeping telemetry path for `TM(3,25)`.
3. Decide whether the `obsw-srdb` version-handshake warning should become a clean-environment requirement.
4. Validate the event/fault path for `TM(5,3)`.
5. Decide the YAMCS runtime execution boundary after OpenSVF-only runtime evidence is stronger.
6. Add reproducibility hardening only after the runtime paths are stable.
