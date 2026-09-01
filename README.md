# OrbitFabric ↔ OpenOBSW/OpenSVF : PoC to Reference Integration

## The Vision

This repository began as a Proof of Concept (PoC) demonstrating a minimal, end-to-end Model-Based Systems Engineering (MBSE) continuity chain for spacecraft software validation. It now also preserves the first validated OpenOBSW/OpenSVF Reference Integration baseline extracted from that evidence.

It bridges:

* **[OrbitFabric Core](https://github.com/FAROTECH/orbitfabric):** the model-first Mission Data Contract framework and semantic source of truth.
* **[OpenOBSW](https://github.com/lipofefeyt/openobsw) & [OpenSVF](https://github.com/lipofefeyt/opensvf):** the flight software execution stack and simulation/ground validation environment.

The goal is not to turn OrbitFabric into flight software, nor to replace OpenOBSW, OpenSVF, XTCE, YAMCS, or PUS tooling.

The goal is to prove that producer-side mission semantics, explicit projection choices, downstream target representations, runtime behavior, and verification evidence can be connected without collapsing ownership between the participating systems.

## Original Goal: The Thin Vertical Slice

The first PoC slice intentionally stays small:

1. Define a minimal OrbitFabric Core Mission Model.
2. Validate it with `orbitfabric lint`.
3. Use a PoC adapter/mapping layer to generate:
   * a flight-side `mission_contract.h`;
   * an OpenSVF-compatible SRDB YAML.
4. Let OpenSVF generate the XTCE/YAMCS mission database.
5. Execute the contracted behavior in OpenOBSW/OpenSVF runtime smoke tests.
6. Validate command, telemetry, and event visibility through OpenSVF/YAMCS.

The first slice focuses on:

* one telemetry parameter;
* one command;
* one event/fault path;
* one housekeeping packet.

For the engineering mapping details, see [Mapping Concept & Vertical Slice Definition](docs/mapping_concept.md).

For the longer-term architectural direction, see [Integration Vision](docs/integration_vision.md).

For the detailed PoC stage history, see [Roadmap](docs/roadmap.md).

For the current validated reference baseline, see [Reference Integration Baseline v0.1](docs/reference_integration_baseline_v0_1.md).

For the extraction history and design sequence, see [Stage 7 Reference Integration Package Extraction](docs/stage7_reference_integration_extraction.md).

## Repository Structure & Data Flow

The repository sits at the integration boundary between a Core-owned mission model and downstream OpenOBSW/OpenSVF execution and verification. It separates semantic input, target projection choices, Adapter implementation, target-facing artifacts, runtime evidence, and historical PoC scaffolding.

```text
orbitfabric_models/
  mission/              OrbitFabric Core-compatible Mission Model
  poc_slice.yaml         Legacy PoC mapping/allocation layer

projection_profiles/     Version-controlled target Projection Profile

integration_package/      Reference Integration Package / Adapter implementation

generated_artifacts/
  flight_software/       Generated OpenOBSW-facing C contract artifacts
  ground_segment/        Generated OpenSVF-facing SRDB artifacts

execution/
  opensvf/               PoC-side OpenSVF spacecraft descriptors
  campaigns/             OpenSVF campaign descriptors
  procedures/            OpenSVF campaign procedures
  yamcs/                 PoC YAMCS runtime/evidence harnesses
  generated/             Local generated runtime/MDB outputs, ignored by git
  evidence/              Local runtime evidence, ignored by git

tools/                   PoC generators and validators

docs/                    Architecture, mapping, stage evidence, and workflow documentation
```

### Source Model vs Legacy Mapping Layer

`orbitfabric_models/mission/` is the OrbitFabric Core-compatible source model.

It is the semantic Mission Model and should validate with:

```bash
orbitfabric lint orbitfabric_models/mission/
```

`orbitfabric_models/poc_slice.yaml` is not the OrbitFabric Core Mission Model.

It is the original PoC mapping/allocation layer used to associate the semantic mission model with integration-specific details such as:

* C identifiers;
* numeric allocation values;
* PUS service/subservice mapping;
* SRDB target names;
* housekeeping set/SID details.

That file remains useful PoC evidence and migration input, but Stage 7 no longer treats it as the future production integration schema.

The reference-integration boundary consumes the OrbitFabric Core v1.2 Integration Input Set and composes it with downstream-owned target/runtime contracts:

```text
OrbitFabric Mission Model
        |
        v
OrbitFabric Core
Core Integration Input Set
        |
        v
Projection Profile
        |
        v
OpenOBSW/OpenSVF Integration Package / Adapter
        |
        +-> OpenOBSW-facing contract
        +-> obsw-srdb contribution
        +-> Integration Result
        |
        v
obsw-srdb target composition
        |
        v
OpenOBSW build/runtime
        |
        v
OpenSVF campaign / YamcsBridge
        |
        v
YAMCS runtime evidence
```

Core remains the semantic authority for mission meaning. The Projection Profile and Adapter own integration-specific projection choices and traceability; obsw-srdb/OpenOBSW own target composition and flight/runtime behavior; OpenSVF and YAMCS retain their native verification and ground-runtime semantics.

## Current Baseline

The selected PoC vertical slice is now closed at the representative integration-evidence level.

Completed baseline:

* [x] Define high-level mapping concepts.
* [x] Define and lint the minimal OrbitFabric Core-compatible Mission Model.
* [x] Generate the contract-only OpenOBSW-facing `mission_contract.h`.
* [x] Generate OpenSVF-compatible SRDB YAML.
* [x] Validate local XTCE/YAMCS MDB generation through OpenSVF tooling.
* [x] Establish OpenSVF pipe-mode execution through `OBCEmulatorAdapter`.
* [x] Validate the representative ping command path.
* [x] Validate live OpenOBSW `TM(3,25)` housekeeping delivery through real OpenSVF `YamcsBridge` into YAMCS archive/MDB classification.
* [x] Validate live OpenOBSW `TM(5,3)` event delivery through real OpenSVF `YamcsBridge` into YAMCS archive/MDB classification.
* [x] Validate the opposite YAMCS-originated `TC(17,1)` direction through OpenSVF into live OpenOBSW and the response TM path back to YAMCS.
* [x] Consolidate the selected telemetry, command, and event paths in the Stage 6.20 final integration evidence matrix.
* [x] Review the durable ownership boundary and PoC asset disposition with the OpenOBSW/OpenSVF maintainer in PR #30.

Representative Stage 6 closure evidence:

```text
Telemetry
  eps.obc.bus_voltage_mv
  -> OpenOBSW TM(3,25)
  -> OpenSVF YamcsBridge
  -> YAMCS archive / MDB classification

Command
  YAMCS TC(17,1)
  -> OpenSVF YamcsBridge
  -> OBCEmulatorAdapter
  -> OpenOBSW
  -> TM(1,1), TM(17,2), TM(1,7)
  -> YAMCS

Event
  eps.voltage_out_of_bounds
  -> OpenOBSW TM(5,3)
  -> OpenSVF YamcsBridge
  -> YAMCS archive / MDB classification
```

This evidence is deliberately narrow. It does not claim production mission integration, hardware-target execution, production FDIR behavior, production commanding security/authorization, or operational deployment hardening.

## Stage 7: Reference Integration Baseline

Stage 7 has reached the first validated **OrbitFabric OpenOBSW/OpenSVF Reference Integration** baseline across the OrbitFabric Core v1.2 Integration Input Set and the audited OpenOBSW/OpenSVF downstream boundaries.

The reference Adapter implementation is frozen at version `0.1.0`.

The generic Projection Profile, Integration Package, and Integration Result contracts remain independently versioned candidate contracts. Adapter `0.1.0` therefore identifies a validated reference implementation baseline, not a claim that the surrounding generic integration architecture is permanently stable.

The repository now preserves both the original PoC evidence and the extracted reference implementation at the boundary between producer and downstream systems. Further work is treated as productionization or integration-architecture evolution rather than as additional evidence required to establish this baseline.

The intended durable chain is:

```text
Core Integration Input Set
+
version-controlled Projection Profile
        ↓
OpenOBSW/OpenSVF Integration Package
        ↓
out-of-process Adapter CLI
        ↓
contract-only OpenOBSW-facing artifact
OpenSVF-compatible SRDB artifact
Integration Result with traceability/provenance
```

The baseline Projection Profile is:

```text
projection_profiles/poc_openobsw_opensvf.yaml
```

It uses Core `{domain,id}` identity for semantic sources and keeps downstream-specific numeric allocations, PUS mapping, HK allocation, and target naming choices outside Core semantics. The long-term allocation/stability policy for those values remains an integration-specific productionization and architecture decision.

The legacy `poc_slice.yaml` remains unchanged as historical PoC evidence and migration/reference material.

See [Stage 7 Reference Integration Package Extraction](docs/stage7_reference_integration_extraction.md) for the extraction history, implementation sequence, and non-goals.

See [Reference Integration Baseline v0.1](docs/reference_integration_baseline_v0_1.md) for the frozen validation boundary and explicit productionization follow-ups.

## Key Ownership Boundaries

The reviewed ownership direction is:

* OrbitFabric Core owns Mission Model semantics and the coherent Core Integration Input Set.
* The Projection Profile records authored target-specific projection choices.
* The OpenOBSW/OpenSVF Integration Package / Adapter owns integration-specific schema, validation, mapping, contribution generation, traceability, provenance, and compatibility checks.
* `obsw-srdb` owns complete target-SRDB composition, collision rules, and target code-generation semantics.
* OpenOBSW owns C11 flight/runtime behavior, including packet framing, command dispatch, HK scheduling, and event materialization.
* OpenSVF owns native simulation, spacecraft loading, campaign/procedure semantics, XTCE generation from the composed SRDB path, and `YamcsBridge`.
* YAMCS owns MDB/runtime interpretation, TM/TC links, archive behavior, and command release semantics.

## Development Workflow

This PoC and Reference Integration are developed through branch-based collaboration.

Use branches and pull requests.

Do not push directly to `main`.

For local setup and collaborator workflow, see [Development Workflow](docs/development_workflow.md).
